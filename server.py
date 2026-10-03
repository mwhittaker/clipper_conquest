#!/usr/bin/env python3
"""Clipper Conquest game server. One file, Python 3.9+ standard library only.

    python3 server.py                 # then open the printed links; the game lives in game-data/

Storage, all in the --data folder:
    game.log     the whole game as JSON lines, one event per line, only ever appended
    photos/      uploaded photos: <photo id>-full.jpg (original) and -web.jpg (small copy)

On start the server replays game.log to rebuild the game, so it can crash or be restarted at
any time. Writes are batched: new events are saved at most once per --flush-interval (1 s by
default, which also suits a Cloud Storage bucket, which allows about one update per second
per file), and a phone only gets its "saved" reply after its event is on disk. Every
completion carries an id chosen by the phone, so a retry after a crash never counts twice.

The server stamps every event with its own clock, so ties never depend on a phone's time.
It also serves the game app (at /), and only the app: the files in WEB_FILES,
never the game data. So players need just one address. HTTPS comes from
whatever sits in front (Caddy, Cloud Run, Fly, a Cloudflare tunnel); see README.md.
"""
import argparse, html, io, json, mimetypes, os, re, sys, threading, time, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TEAMS = {'red': 'Red', 'blue': 'Blue'}
SPOT_WINDOW = 5 * 60 * 1000   # a location older than this no longer counts toward its team's spot
MAX_PHOTO = 25 * 1024 * 1024
MAX_JSON = 64 * 1024
ID_RE = re.compile(r'^[A-Za-z0-9_-]{6,64}$')
# What the server hands out: only the game app and what it loads, nothing else,
# never game-data/. The guide and the replay site live on GitHub Pages.
WEB_FILES = {'app.html', 'app.js', 'mobile.js', 'mobile.css', 'replay-core.js', 'challenges.json',
             'sf_neighborhoods.geojson'}


# ----- the challenges: players get the first three per neighborhood (same as trios() in replay-core.js) -----
def md(s):
    s = html.escape(s or '')
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'<i>\1</i>', s)


def fail_kind(f):
    f = (f or '').lower()
    return 'one-shot' if 'one-shot' in f or 'one shot' in f else 'retryable' if f.startswith('retry') else ''


def trios(src):
    out = {}
    for name, hood in src.items():
        out[name] = [{'title': md(c['title']), 'where': md(c['where']), 'fail': fail_kind(c['failable'])}
                     for c in hood['candidates'][:3]]
    return out


class Log:
    """The append-only game log, written in batches by one background thread."""

    def __init__(self, path, interval):
        self.path, self.interval = path, interval
        self.pending, self.taken, self.written, self.writes = [], 0, 0, 0
        self.cv = threading.Condition()
        threading.Thread(target=self._run, daemon=True).start()

    def read(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, 'rb+') as f:       # a crash mid-write can leave half a line at the end:
            raw = f.read()                        # cut it off, or the next event would be glued onto it
            if raw and not raw.endswith(b'\n'):
                keep = raw.rfind(b'\n') + 1
                print(f'game.log ends with a half-written event (a crash mid-write?); dropping {len(raw) - keep} bytes',
                      file=sys.stderr)
                f.truncate(keep)
        out = []
        with open(self.path, encoding='utf-8') as f:
            for n, line in enumerate(f, 1):
                try:
                    out.append(json.loads(line))
                except ValueError:
                    print(f'game.log line {n} is damaged (a crash mid-write?); skipping it', file=sys.stderr)
        return out

    def append(self, rec):
        """Queue one event; returns a ticket for wait()."""
        with self.cv:
            self.pending.append(json.dumps(rec, ensure_ascii=False, separators=(',', ':')) + '\n')
            self.cv.notify_all()
            return self.taken + 1              # it goes out with the next batch taken

    def wait(self, ticket, timeout=15):
        with self.cv:
            return self.cv.wait_for(lambda: self.written >= ticket, timeout)

    def _run(self):
        while True:
            with self.cv:
                self.cv.wait_for(lambda: self.pending)
                lines, self.pending = self.pending, []
                self.taken += 1
                batch = self.taken
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(''.join(lines))
                f.flush()
                os.fsync(f.fileno())
            with self.cv:
                self.written, self.writes = batch, self.writes + 1
                self.cv.notify_all()
            time.sleep(self.interval)          # at most one write per interval


class Game:
    """Everything that has happened, rebuilt from the log. One lock guards it all."""

    def __init__(self, data, challenges, interval):
        self.data, self.challenges = data, challenges
        os.makedirs(os.path.join(data, 'photos'), exist_ok=True)
        self.lock = threading.Lock()
        self.log = Log(os.path.join(data, 'game.log'), interval)
        self.seq = 0
        self.checked_in = {}   # (team, name) -> when that player's phone last checked in (memory only)
        self.cfg = {'title': 'Clipper Conquest', 'start': None, 'end': None}
        self.first_start = None   # the earliest start that actually happened (a game can stop and start again)
        self.comps = {}        # completion id -> event (only ones still standing)
        self.slot = {}         # (team, hood, ci) -> completion id
        self.fails = {}        # failure id -> event: a team missed a one-shot challenge
        self.fail_slot = {}    # (team, hood, ci) -> failure id
        self.seen = set()      # every completion and failure id ever used, for retries
        # Photos belong to a team's challenge, not to one completion, so undoing and redoing a
        # completion (or a failure) never loses them. A challenge can have any number.
        self.photos = {}       # photo id -> {'id', 't', 'team', 'hood', 'ci', 'by', 'full': file, 'web': file}
        self.pings = []        # [t, team, by, lat, lon]
        for rec in self.log.read():
            self._apply(rec)
            self.seq = max(self.seq, rec.get('seq', 0))

    # ----- time and phase -----
    def now(self):
        return int(time.time() * 1000)

    def phase(self, t=None):
        t = self.now() if t is None else t
        s, e = self.cfg['start'], self.cfg['end']
        if not s or not e:
            return 'setup'
        return 'before' if t < s else 'playing' if t < e else 'over'

    # ----- the log -----
    def _apply(self, r):
        k = r['type']
        if k == 'setup':
            old, end = self.cfg['start'], self.cfg['end']
            if 'start' in r and old is not None and old <= r['t'] and (end is None or old < end):
                self.first_start = min(self.first_start or old, old)     # that start had arrived: play happened
            self.cfg.update({x: r[x] for x in ('title', 'start', 'end') if x in r})
        elif k == 'complete':
            self.seen.add(r['id'])
            self.comps[r['id']] = r
            self.slot[(r['team'], r['hood'], r['ci'])] = r['id']
        elif k == 'fail':
            self.seen.add(r['id'])
            self.fails[r['id']] = r
            self.fail_slot[(r['team'], r['hood'], r['ci'])] = r['id']
        elif k == 'remove':                     # undoes a completion or a failure
            c = self.comps.pop(r['completion'], None)
            if c:
                self.slot.pop((c['team'], c['hood'], c['ci']), None)
            f = self.fails.pop(r['completion'], None)
            if f:
                self.fail_slot.pop((f['team'], f['hood'], f['ci']), None)
        elif k == 'photo':
            p = self.photos.setdefault(r['id'], {x: r[x] for x in ('id', 't', 'team', 'hood', 'ci')} | {'by': r.get('by', '')})
            p[r['kind']] = r['file']
        elif k == 'photo_remove':
            self.photos.pop(r['photo'], None)
        elif k == 'ping':
            self.pings.append([r['t'], r['team'], r.get('by', ''), r['lat'], r['lon']])

    def _record(self, rec):
        """Call with the lock held. Stamps, applies and queues an event; returns a log ticket."""
        self.seq += 1
        rec = {'seq': self.seq, 't': self.now(), **rec}
        self._apply(rec)
        return rec, self.log.append(rec)

    def commit(self, fn):
        """Run fn under the lock; if it recorded an event, wait until that event is on disk."""
        with self.lock:
            status, body, ticket = fn()
        if ticket and not self.log.wait(ticket):
            return 503, {'error': 'Could not save. Try again.'}
        return status, body

    # ----- what phones see -----
    def photo_list(self, team=None, admin=False):
        """All photos in time order; the other team's addresses are left out until the game ends."""
        over = self.phase() == 'over'
        out = []
        for p in sorted(self.photos.values(), key=lambda p: p['t']):
            f = p.get('web') or p.get('full')
            visible = admin or over or p['team'] == team
            out.append({k: p[k] for k in ('id', 't', 'team', 'hood', 'ci', 'by')} |
                       {'url': f"/photos/{f}?team={team or ''}" if f and visible else None})
        return out

    def view(self, team):
        with self.lock:
            comps = sorted(self.comps.values(), key=lambda c: (c['t'], c['seq']))
            now, phase = self.now(), self.phase()
            return {'now': now, 'seq': self.seq, 'phase': phase, 'game': dict(self.cfg),
                    'completions': [{k: c[k] for k in ('id', 't', 'team', 'hood', 'ci', 'by')} for c in comps],
                    'fails': self.fail_list(), 'photos': self.photo_list(team),
                    'spots': self.spots(now) if phase == 'playing' else {}}

    def spots(self, now):
        """Where each team is, for everyone's map: the average of its players' latest locations
        from the last 5 minutes. {team: {lat, lon, t, players}}"""
        latest = {}
        for t, team, by, lat, lon in reversed(self.pings):    # newest first (they're logged in order)
            if now - t > SPOT_WINDOW:
                break
            latest.setdefault((team, by), (t, lat, lon))
        out = {}
        for team in TEAMS:
            ps = [v for (tm, _), v in latest.items() if tm == team]
            if ps:
                out[team] = {'lat': sum(p[1] for p in ps) / len(ps), 'lon': sum(p[2] for p in ps) / len(ps),
                             't': max(p[0] for p in ps), 'players': len(ps)}
        return out

    def fail_list(self):
        return [{k: f[k] for k in ('id', 't', 'team', 'hood', 'ci', 'by')}
                for f in sorted(self.fails.values(), key=lambda f: (f['t'], f['seq']))]

    # ----- exports -----
    def _title(self, hood, ci):
        try:
            return html.unescape(re.sub(r'<[^>]+>', '', self.challenges[hood][ci]['title']))
        except (KeyError, IndexError):
            return f'Challenge {ci + 1}'

    def album_zip(self):
        """Every photo at full size, named by time, team, neighborhood and challenge."""
        with self.lock:
            photos = sorted((dict(p) for p in self.photos.values()), key=lambda p: p['t'])
        buf, used = io.BytesIO(), set()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as z:
            for p in photos:
                f = p.get('full') or p.get('web')
                if not f:
                    continue
                base = (f"{time.strftime('%H-%M', time.localtime(p['t'] / 1000))} {TEAMS[p['team']]} - "
                        f"{p['hood'].replace('/', '-')} - {self._title(p['hood'], p['ci'])}" + (f" ({p['by']})" if p['by'] else ''))
                base = 'Clipper Conquest photos/' + re.sub(r'[\\:*?"<>|]', '', base)
                name, n = base + '.jpg', 1
                while name in used:                          # several photos in the same minute
                    n += 1
                    name = f'{base} {n}.jpg'
                used.add(name)
                z.write(os.path.join(self.data, 'photos', f), name)
        return buf.getvalue()

    def replay_game(self):
        """The game in the replay format (see replay-core.js), and each photo's file:
        returns (game, {path in the replay: file in photos/})."""
        with self.lock:
            comps = sorted(self.comps.values(), key=lambda c: (c['t'], c['seq']))
            photos = sorted((dict(p) for p in self.photos.values()), key=lambda p: p['t'])
            pings, cfg, fails = list(self.pings), dict(self.cfg), self.fail_list()
            first_start = self.first_start
        players = {t: sorted({c['by'] for c in comps if c['team'] == t} | {p[2] for p in pings if p[1] == t} - {''})
                   for t in TEAMS}
        by_slot, files = {}, {}                              # each completion and failure lists its photos, oldest first
        for p in photos:
            f = p.get('web') or p.get('full')
            if f:
                by_slot.setdefault((p['team'], p['hood'], p['ci']), []).append(f"photos/{p['id']}.jpg")
                files[f"photos/{p['id']}.jpg"] = f
        entry = lambda e: {k: e[k] for k in ('id', 't', 'team', 'hood', 'ci', 'by')} | {
            'photos': by_slot.get((e['team'], e['hood'], e['ci']), [])}
        game = {
            'format': 'clipper-conquest-replay', 'version': 1, 'title': cfg['title'],
            'start': min(x for x in (first_start, cfg['start']) if x), 'end': cfg['end'],   # everything, every stretch
            'teams': {t: {'name': n, 'players': players[t]} for t, n in TEAMS.items()},
            'challenges': {h: [{'title': c['title'], 'where': c.get('where', '')} for c in v] for h, v in self.challenges.items()},
            'completions': [entry(c) for c in comps], 'fails': [entry(f) for f in fails],
            'pings': {t: sorted([p[0], p[3], p[4]] for p in pings if p[1] == t) for t in TEAMS},
        }
        return game, files

    def replay_zip(self):
        """The replay file: game.json plus the small copy of every photo."""
        game, files = self.replay_game()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            for path, f in files.items():
                z.write(os.path.join(self.data, 'photos', f), path, compress_type=zipfile.ZIP_STORED)
            z.writestr('game.json', json.dumps(game, ensure_ascii=False), compress_type=zipfile.ZIP_DEFLATED)
        return buf.getvalue()


def make_handler(game, web, home):
    web = os.path.realpath(web) if web else None

    class H(BaseHTTPRequestHandler):
        server_version = 'ClipperConquest/0.1'

        def log_message(self, fmt, *args):                 # one short line per request
            sys.stderr.write(f"{self.log_date_time_string()} {self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")

        # ----- plumbing -----
        def send(self, status, body=b'', ctype='application/json', extra=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body).encode()
            elif isinstance(body, str):
                body = body.encode()
            self.send_response(status)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store' if ctype == 'application/json' else 'no-cache')
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(body)

        def body(self, limit):
            n = int(self.headers.get('Content-Length') or 0)
            if n > limit:
                raise ValueError('too large')
            return self.rfile.read(n)

        def json_body(self):
            try:
                return json.loads(self.body(MAX_JSON) or b'{}')
            except ValueError:
                raise ValueError('bad JSON')


        # ----- GET -----
        def do_GET(self):
            u = urlparse(self.path)
            q, p = parse_qs(u.query), u.path
            if p == '/api/state':
                team, name = (q.get('team') or [''])[0], (q.get('name') or [''])[0].strip()[:40]
                if team in TEAMS and name:                      # for the admin page's "who's connected"
                    game.checked_in[(team, name)] = game.now()
                return self.send(200, game.view(team))
            if p.startswith('/photos/'):
                return self.photo(p[8:], q)
            if p == '/admin':                                # no key: the organizer trusts the players
                return self.send(200, ADMIN_HTML, 'text/html; charset=utf-8')
            if p.startswith('/api/admin/'):
                return self.admin_get(p[11:])
            if p == '/api/replay.json':                         # the finished game, for the app's replay
                if game.phase() != 'over':
                    return self.send(403, {'error': 'available when the game is over'})
                g, files = game.replay_game()
                return self.send(200, {'game': g, 'photos': {k: f'/photos/{f}' for k, f in files.items()}})
            return self.static(p)
        do_HEAD = do_GET

        def photo(self, name, q):
            m = re.fullmatch(r'([A-Za-z0-9_-]+)-(full|web)\.jpg', name)
            if not m:
                return self.send(404, {'error': 'no such photo'})
            with game.lock:
                ph = game.photos.get(m.group(1))
                ok = ph and (game.phase() == 'over' or ph['team'] == (q.get('team') or [''])[0])
            if not ok:
                return self.send(403, {'error': 'hidden until the game ends'})
            path = os.path.join(game.data, 'photos', name)
            if not os.path.exists(path):
                return self.send(404, {'error': 'no such photo'})
            with open(path, 'rb') as f:
                self.send(200, f.read(), 'image/jpeg')

        def static(self, p):
            if not web:
                return self.send(404, {'error': 'not found'})
            name = home if p == '/' else p.lstrip('/')    # players land on the app
            allowed = name in WEB_FILES
            path = os.path.realpath(os.path.join(web, name))
            if not allowed or not path.startswith(web + os.sep) or not os.path.isfile(path):
                return self.send(404, 'Not found', 'text/plain')
            with open(path, 'rb') as f:
                self.send(200, f.read(), mimetypes.guess_type(path)[0] or 'application/octet-stream')

        def admin_get(self, what):
            day = time.strftime('%Y-%m-%d', time.localtime((game.cfg['start'] or game.now()) / 1000))
            if what == 'state':
                with game.lock:
                    now = game.now()
                    return self.send(200, {
                        'now': now, 'phase': game.phase(), 'game': dict(game.cfg),
                        'completions': len(game.comps), 'photos': len(game.photos),
                        'pings': len(game.pings), 'seq': game.seq, 'log_writes': game.log.writes,   # for tests
                        'players': [{'team': t, 'name': n, 'ago': now - seen} for (t, n), seen in sorted(game.checked_in.items())]})
            if what == 'export/photos.zip':
                return self.send(200, game.album_zip(), 'application/zip',
                                 {'Content-Disposition': f'attachment; filename="clipper-conquest-photos-{day}.zip"'})
            if what == 'export/replay.zip':
                return self.send(200, game.replay_zip(), 'application/zip',
                                 {'Content-Disposition': f'attachment; filename="clipper-conquest-{day}.ccreplay"'})
            return self.send(404, {'error': 'not found'})

        # ----- POST -----
        def do_POST(self):
            u = urlparse(self.path)
            q, p = parse_qs(u.query), u.path
            try:
                if p == '/api/photo':
                    return self.send(*self.upload(q))
                b = self.json_body()
                if p == '/api/complete':
                    return self.send(*game.commit(lambda: complete(b)))
                if p == '/api/photo/remove':
                    return self.send(*game.commit(lambda: photo_remove(b)))
                if p == '/api/unfail':
                    return self.send(*game.commit(lambda: unfail(b)))
                if p == '/api/fail':
                    return self.send(*game.commit(lambda: fail(b)))
                if p == '/api/uncomplete':
                    return self.send(*game.commit(lambda: uncomplete(b)))
                if p == '/api/ping':
                    return self.send(*game.commit(lambda: ping(b)))
                if p.startswith('/api/admin/'):
                    return self.send(*game.commit(lambda: admin(p[11:], b)))
            except ValueError as e:
                return self.send(400, {'error': str(e)})
            return self.send(404, {'error': 'not found'})

        def upload(self, q):
            g = lambda k, d='': (q.get(k) or [d])[0]
            pid, kind = g('id'), g('kind', 'full')
            if not ID_RE.match(pid):
                raise ValueError('each photo needs an id made by the phone')
            if kind not in ('full', 'web'):
                raise ValueError('kind must be full or web')
            try:
                slot = check_slot({'team': g('team'), 'hood': g('hood'), 'ci': int(g('ci', '-1'))})
            except ValueError:
                raise ValueError('photo needs team, hood and ci')
            with game.lock:
                if game.phase() in ('setup', 'before'):
                    return 409, {'error': 'The game hasn’t started yet.'}
            data = self.body(MAX_PHOTO)
            if not data.startswith(b'\xff\xd8'):
                raise ValueError('photos must be JPEGs')
            name = f'{pid}-{kind}.jpg'
            path, tmp = os.path.join(game.data, 'photos', name), os.path.join(game.data, 'photos', f'.{name}.tmp')
            with open(tmp, 'wb') as f:                       # write, then swap in, so a crash never leaves half a photo
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)

            def rec():
                team, hood, ci = slot
                have = game.photos.get(pid)
                if have and (have['team'], have['hood'], have['ci']) != slot:
                    return 409, {'error': 'that photo id belongs to another challenge'}, None
                if have and have.get(kind) == name:          # a retry: already recorded
                    return 200, {'ok': True, 'photo': pid}, None
                r, t = game._record({'type': 'photo', 'id': pid, 'team': team, 'hood': hood, 'ci': ci,
                                     'by': g('by')[:40], 'kind': kind, 'file': name, 'bytes': len(data)})
                return 200, {'ok': True, 'photo': pid}, t
            return game.commit(rec)

    # ----- the rules for each change (called with the lock held) -----
    def check_slot(b):
        team, hood, ci = b.get('team'), b.get('hood'), b.get('ci')
        if team not in TEAMS:
            raise ValueError('team must be red or blue')
        if hood not in game.challenges or not isinstance(ci, int) or not 0 <= ci < len(game.challenges[hood]):
            raise ValueError('unknown neighborhood or challenge')
        return team, hood, ci

    def complete(b):
        cid = b.get('id', '')
        if not ID_RE.match(cid):
            raise ValueError('each completion needs an id made by the phone')
        if cid in game.seen:                                 # a retry: the first try landed
            c = game.comps.get(cid)
            return 200, {'ok': True, 'completion': c, 'retry': True}, None
        team, hood, ci = check_slot(b)
        if game.phase() != 'playing':
            return 409, {'error': {'setup': 'The game isn’t set up yet.', 'before': 'The game hasn’t started yet.',
                                   'over': 'Time’s up: the game is over.'}[game.phase()]}, None
        if (team, hood, ci) in game.slot:
            return 409, {'error': 'Your team already completed this challenge.', 'completion': game.comps[game.slot[(team, hood, ci)]]}, None
        if (team, hood, ci) in game.fail_slot:
            return 409, {'error': 'Your team marked this one as failed. Undo that first.'}, None
        rec, t = game._record({'type': 'complete', 'id': cid, 'team': team, 'hood': hood, 'ci': ci, 'by': str(b.get('by', ''))[:40]})
        return 200, {'ok': True, 'completion': rec}, t

    def fail(b):
        """A team marks a one-shot challenge as failed. It can undo that (a misclick) while the game is on."""
        fid = b.get('id', '')
        if not ID_RE.match(fid):
            raise ValueError('each failure needs an id made by the phone')
        if fid in game.seen:
            return 200, {'ok': True, 'fail': game.fails.get(fid), 'retry': True}, None
        team, hood, ci = check_slot(b)
        if game.challenges[hood][ci].get('fail') != 'one-shot':
            return 409, {'error': 'Only one-shot challenges can be marked as failed.'}, None
        if game.phase() != 'playing':
            return 409, {'error': 'Only while the game is on.'}, None
        if (team, hood, ci) in game.slot:
            return 409, {'error': 'Your team already completed this challenge.'}, None
        if (team, hood, ci) in game.fail_slot:
            return 200, {'ok': True, 'fail': game.fails[game.fail_slot[(team, hood, ci)]]}, None
        rec, t = game._record({'type': 'fail', 'id': fid, 'team': team, 'hood': hood, 'ci': ci, 'by': str(b.get('by', ''))[:40]})
        return 200, {'ok': True, 'fail': rec}, t

    def unfail(b):
        team, hood, ci = check_slot(b)
        if game.phase() != 'playing':
            return 409, {'error': 'Only while the game is on.'}, None
        fid = game.fail_slot.get((team, hood, ci))
        if not fid:
            return 200, {'ok': True}, None
        rec, t = game._record({'type': 'remove', 'completion': fid, 'by': str(b.get('by', ''))[:40]})
        return 200, {'ok': True}, t

    def photo_remove(b):
        pid = b.get('photo')
        if pid not in game.photos:
            return 200, {'ok': True}, None                   # already gone (a retry)
        if game.phase() not in ('playing', 'over'):
            return 409, {'error': 'The game hasn’t started yet.'}, None
        rec, t = game._record({'type': 'photo_remove', 'photo': pid, 'by': str(b.get('by', ''))[:40]})
        return 200, {'ok': True}, t

    def uncomplete(b):
        team, hood, ci = check_slot(b)
        if game.phase() != 'playing':
            return 409, {'error': 'Only while the game is on.'}, None
        cid = game.slot.get((team, hood, ci))
        if not cid:
            return 200, {'ok': True}, None
        rec, t = game._record({'type': 'remove', 'completion': cid, 'by': str(b.get('by', ''))[:40]})
        return 200, {'ok': True}, t

    def ping(b):
        team, lat, lon = b.get('team'), b.get('lat'), b.get('lon')
        if team not in TEAMS or not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            raise ValueError('ping needs team, lat, lon')
        if game.phase() != 'playing':
            return 200, {'ok': True, 'ignored': True}, None
        rec, t = game._record({'type': 'ping', 'team': team, 'by': str(b.get('by', ''))[:40],
                               'lat': round(lat, 5), 'lon': round(lon, 5)})
        return 200, {'ok': True}, t

    def admin(what, b):
        if what == 'setup':
            ch = {k: b[k] for k in ('title', 'start', 'end') if k in b}
            if game.phase() == 'playing' and 'start' in ch and ch['start'] != game.cfg['start']:
                return 409, {'error': 'The game is on: you can change the end, but not the start.'}, None
            s, e = ch.get('start', game.cfg['start']), ch.get('end', game.cfg['end'])
            if s is not None and e is not None and e <= s:
                raise ValueError('The end must be after the start.')
            rec, t = game._record({'type': 'setup', **ch})
        elif what == 'start-now':                            # keeps a later end time; otherwise runs 5 hours
            s0 = game.now()
            e = game.cfg['end'] if game.cfg['end'] and game.cfg['end'] > s0 else s0 + 5 * 3600 * 1000
            rec, t = game._record({'type': 'setup', 'start': s0, 'end': e})
        elif what == 'end-now':
            rec, t = game._record({'type': 'setup', 'end': game.now()})
        else:
            return 404, {'error': 'not found'}, None
        return 200, {'ok': True, 'event': rec}, t

    return H


ADMIN_HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Clipper Conquest admin</title>
<style>
  :root { --red: #C42847; --blue: #1D6FB8; --ink: #1C1E21; --muted: #6A7076; --line: #D9DDE1; --soft: #F4F5F6; --go: #2E8B57; }
  * { box-sizing: border-box; margin: 0; }
  body { font: 15px/1.45 system-ui, sans-serif; color: var(--ink); background: #fff; max-width: 560px; margin: 0 auto; padding: 28px 16px 48px; }
  h2 { font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 28px 0 10px; }
  .state { background: var(--soft); border-radius: 16px; padding: 20px; text-align: center; }
  .phase { display: inline-block; font-size: 13px; font-weight: 700; padding: 3px 12px; border-radius: 999px; background: #E3E6E9; color: var(--muted); }
  .phase.playing { background: #DDF1E4; color: #1E6B3A; } .phase.over { background: var(--ink); color: #fff; }
  .clock { font-size: 52px; font-weight: 800; font-variant-numeric: tabular-nums; letter-spacing: -.01em; line-height: 1.1; margin-top: 10px; }
  .sub { color: var(--muted); }
  .times { margin-top: 10px; font-size: 13.5px; color: var(--muted); }
  .row { display: flex; gap: 10px; flex-wrap: wrap; }
  .row > * { flex: 1; min-width: 150px; }
  button { font: inherit; font-weight: 700; padding: 12px 14px; border-radius: 10px; border: 1px solid var(--ink); background: var(--ink); color: #fff; cursor: pointer; }
  button.ghost { background: #fff; color: var(--ink); border-color: var(--line); }
  button.danger { background: #fff; color: var(--red); border-color: var(--red); }
  button.solid-danger { background: var(--red); border-color: var(--red); }
  button:disabled { opacity: .5; cursor: default; }
  label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; font-weight: 600; color: var(--muted); }
  input { font: inherit; font-size: 15px; padding: 10px 12px; border: 1px solid var(--line); border-radius: 10px; color: var(--ink); }
  /* each time shows as "Sep 12 9:30 AM"; tapping it opens the browser's own date-time picker */
  .tf { position: relative; display: block; }
  .tf input { position: absolute; inset: 0; width: 100%; opacity: 0; pointer-events: none; }
  .tbtn { width: 100%; text-align: left; background: #fff; color: var(--ink); border-color: var(--line); font-weight: 600; }
  .tbtn:disabled { background: var(--soft); color: var(--muted); opacity: 1; }
  [hidden] { display: none !important; }
  .hint { font-size: 13px; color: var(--muted); margin-top: 8px; }
  .teams { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .team { border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; }
  .team h3 { font-size: 14px; margin-bottom: 6px; } .team.red h3 { color: var(--red); } .team.blue h3 { color: var(--blue); }
  .team ul { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 4px; }
  .team li { display: flex; align-items: center; gap: 8px; }
  .team li i { width: 8px; height: 8px; border-radius: 50%; background: var(--go); flex: none; }
  .team li.away { color: var(--muted); } .team li.away i { background: #C4CAD0; }
  .team li small { margin-left: auto; color: var(--muted); font-size: 12px; }
  .none { color: var(--muted); font-size: 13.5px; }
  #msg { color: var(--red); min-height: 1.4em; margin-top: 10px; font-size: 14px; }
  #msg.ok { color: var(--go); }
  dialog { margin: auto; border: 0; border-radius: 16px; padding: 22px; max-width: min(360px, calc(100% - 32px)); box-shadow: 0 12px 40px rgba(0,0,0,.25); }
  dialog::backdrop { background: rgba(28,30,33,.45); }
  dialog h3 { font-size: 18px; margin-bottom: 6px; }
  dialog p { color: var(--muted); margin-bottom: 18px; }
  @media (max-width: 600px) {   /* on a phone: a sheet from the bottom, like the game app */
    dialog { margin: auto 0 0; width: 100%; max-width: 100%; border-radius: 18px 18px 0 0; padding-bottom: 28px; }
  }
</style></head><body>

<section class="state">
  <span class="phase" id="phase"></span>
  <div class="clock" id="clock">–:––:––</div>
  <div class="sub" id="sub"></div>
  <div class="times" id="times"></div>
</section>
<p id="msg" role="status"></p>

<div class="row">
  <button id="startnow">Start now</button>
  <button class="danger" id="endnow">End now</button>
</div>

<h2>Game times</h2>
<div class="row">
  <label>Start<span class="tf"><button type="button" class="tbtn" id="start-btn"></button><input id="start" type="datetime-local" tabindex="-1" aria-hidden="true"></span></label>
  <label>End<span class="tf"><button type="button" class="tbtn" id="end-btn"></button><input id="end" type="datetime-local" tabindex="-1" aria-hidden="true"></span></label>
</div>
<p class="hint" id="startnote" hidden>The game is on: you can change the end, but not the start.</p>

<h2>Who's connected</h2>
<div class="teams">
  <div class="team red"><h3>Red</h3><ul id="p-red"></ul></div>
  <div class="team blue"><h3>Blue</h3><ul id="p-blue"></ul></div>
</div>

<h2>Downloads</h2>
<div class="row">
  <button class="ghost" id="album">All photos</button>
  <button class="ghost" id="replay">Replay file</button>
</div>
<p class="hint" id="counts"></p>

<dialog id="endconfirm">
  <h3>End the game now?</h3>
  <p>Players can't complete anything after this.</p>
  <div class="row"><button class="ghost" id="end-cancel">Cancel</button><button class="solid-danger" id="end-yes">End game</button></div>
</dialog>


<script>
const $ = s => document.querySelector(s);
const esc = v => String(v).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let S = null, skew = 0;
async function api(path, body) {
  const r = await fetch('/api/admin/' + path, body === undefined ? {}
    : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = (r.headers.get('Content-Type') || '').includes('json') ? await r.json() : r;
  if (!r.ok) throw new Error(j.error || r.status);
  return j;
}
const act = fn => async () => { try { $('#msg').textContent = ''; $('#msg').className = ''; await fn(); await load(); } catch (e) { $('#msg').textContent = e.message; } };
const toLocal = t => t ? new Date(t - new Date(t).getTimezoneOffset() * 60e3).toISOString().slice(0, 16) : '';
const fromLocal = v => v ? new Date(v).getTime() : null;
// "Sep 12 9:30 AM" (no year); an end on the same day shows just its time
function when(t) {
  const d = new Date(t), h = d.getHours();
  return `${d.toLocaleString('en-US', { month: 'short' })} ${d.getDate()} ${h % 12 || 12}:${String(d.getMinutes()).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`;
}
const sameDay = (a, b) => new Date(a).toDateString() === new Date(b).toDateString();
const ago = ms => ms < 60e3 ? 'now' : ms < 3600e3 ? `${Math.round(ms / 60e3)} min ago` : `${Math.round(ms / 3600e3)} h ago`;
async function load() {
  S = await api('state');
  skew = S.now - Date.now();
  $('#phase').textContent = { setup: 'Not scheduled', before: 'Not started', playing: 'Playing', over: 'Game over' }[S.phase];
  $('#phase').className = 'phase ' + S.phase;
  const g = S.game;
  $('#times').textContent = g.start ? `${when(g.start)} to ${sameDay(g.start, g.end) ? when(g.end).split(' ').slice(2).join(' ') : when(g.end)}`
    : 'No start and end time yet';
  for (const k of ['start', 'end']) {
    $('#' + k + '-btn').textContent = g[k] ? when(g[k]) : 'Pick a time';
    if (document.activeElement.id !== k) $('#' + k).value = toLocal(g[k]);
  }
  for (const team of ['red', 'blue']) {                     // connected = checked in within the last minute
    const ps = S.players.filter(p => p.team === team);
    $('#p-' + team).innerHTML = ps.length ? ps.map(p => `<li class="${p.ago > 60e3 ? 'away' : ''}"><i></i>${esc(p.name)}<small>${p.ago > 60e3 ? ago(p.ago) : ''}</small></li>`).join('')
      : '<li class="none">Nobody yet</li>';
  }
  $('#counts').textContent = `${S.completions} challenges completed, ${S.photos} photos so far.`;
  $('#start-btn').disabled = S.phase === 'playing';
  $('#startnote').hidden = S.phase !== 'playing';
  $('#startnow').textContent = S.phase === 'over' ? 'Start again' : 'Start now';
  $('#startnow').disabled = S.phase === 'playing';
  $('#endnow').disabled = S.phase !== 'playing';
  $('#album').disabled = !S.photos;
  tick();
}
function tick() {
  if (!S) return;
  const now = Date.now() + skew, g = S.game;
  let ms = null, sub = 'Pick a start and end time, or press Start now';
  if (S.phase === 'before') { ms = g.start - now; sub = 'until the game starts'; }
  if (S.phase === 'playing') { ms = g.end - now; sub = 'left in the game'; }
  if (S.phase === 'over') { ms = 0; sub = 'The game is over'; }
  if (ms !== null) {
    ms = Math.max(0, ms);
    $('#clock').textContent = `${Math.floor(ms / 3600e3)}:${String(Math.floor(ms / 60e3) % 60).padStart(2, '0')}:${String(Math.floor(ms / 1e3) % 60).padStart(2, '0')}`;
  } else $('#clock').textContent = '–:––:––';
  $('#sub').textContent = sub;
  if ((S.phase === 'before' && now >= g.start) || (S.phase === 'playing' && now >= g.end)) load();
}
// Tapping a time opens the browser's picker; each time saves as soon as it's picked.
for (const k of ['start', 'end']) $('#' + k + '-btn').onclick = () => {
  const i = $('#' + k);
  try { i.showPicker(); } catch (e) { i.style.pointerEvents = 'auto'; i.focus(); }   // older browsers: focus the field instead
};
for (const k of ['start', 'end']) $('#' + k).addEventListener('change', act(async () => {
  const v = fromLocal($('#' + k).value);
  if (v) { await api('setup', { [k]: v }); saved(); }
}));
function saved() { const m = $('#msg'); m.textContent = 'Saved'; m.className = 'ok'; setTimeout(() => { if (m.textContent === 'Saved') { m.textContent = ''; m.className = ''; } }, 1500); }
$('#startnow').onclick = act(() => api('start-now', {}));
$('#endnow').onclick = () => $('#endconfirm').showModal();   // ask first
$('#end-cancel').onclick = () => $('#endconfirm').close();
$('#end-yes').onclick = () => { $('#endconfirm').close(); act(() => api('end-now', {}))(); };
function save(blob, name) { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 30e3); }
const nameOf = r => (r.headers.get('Content-Disposition').match(/filename="([^"]+)"/) || [])[1];
$('#album').onclick = act(async () => { const r = await api('export/photos.zip'); save(await r.blob(), nameOf(r)); });
$('#replay').onclick = act(async () => { const r = await api('export/replay.zip'); save(await r.blob(), nameOf(r)); });
load(); setInterval(load, 4000); setInterval(tick, 1000);
</script></body></html>'''


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description='Clipper Conquest game server')
    ap.add_argument('--data', default=os.environ.get('CLIPPER_DATA', os.path.join(here, 'game-data')), help='folder for game.log and photos')
    ap.add_argument('--web', default=os.environ.get('CLIPPER_WEB', here),
                    help='folder with the pages and challenges.json (default: this file\'s folder)')
    ap.add_argument('--home', default='app.html', help='page players land on at /')
    ap.add_argument('--host', default=os.environ.get('HOST', '0.0.0.0'))
    ap.add_argument('--port', type=int, default=int(os.environ.get('PORT', 8080)))
    ap.add_argument('--flush-interval', type=float, default=1.0, help='seconds between log writes (default 1)')
    a = ap.parse_args()

    os.makedirs(a.data, exist_ok=True)
    with open(os.path.join(a.web, 'challenges.json'), encoding='utf-8') as f:
        challenges = trios(json.load(f))
    game = Game(a.data, challenges, a.flush_interval)
    ThreadingHTTPServer.request_queue_size = 64   # the default (5) drops connections when many phones ping at once
    srv = ThreadingHTTPServer((a.host, a.port), make_handler(game, a.web, a.home))
    shown = 'localhost' if a.host in ('0.0.0.0', '') else a.host
    print(f'Clipper Conquest server: {len(game.comps)} completions, {len(game.pings)} pings loaded from {a.data}/game.log')
    print(f'  players: http://{shown}:{a.port}/')
    print(f'  admin:   http://{shown}:{a.port}/admin')
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
