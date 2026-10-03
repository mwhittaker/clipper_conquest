#!/usr/bin/env python3
"""Plays a short game against a real clipper_server.py process and checks the essentials:
setup, completions and retries, photo privacy, batched saving, surviving a hard kill and a
damaged log line, the end of the game, and both exports.
    python3 server_test.py           (uses a temporary data folder and port 8091)
"""
import io, json, os, re, signal, subprocess, sys, tempfile, threading, time, urllib.error, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('SMOKE_PORT', 8091))
BASE = f'http://127.0.0.1:{PORT}'
JPEG = b'\xff\xd8\xff\xe0' + b'fake-jpeg-bytes' * 50 + b'\xff\xd9'
passed = 0


def check(cond, what):
    global passed
    if not cond:
        print('FAIL', what); sys.exit(1)
    passed += 1
    print('ok  ', what)


def req(path, body=None, raw=None, method=None):
    headers = {}
    data = None
    if raw is not None:
        data, headers['Content-Type'] = raw, 'image/jpeg'
    elif body is not None:
        data, headers['Content-Type'] = json.dumps(body).encode(), 'application/json'
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            b = resp.read()
            return resp.status, (json.loads(b) if resp.headers['Content-Type'] == 'application/json' else b)
    except urllib.error.HTTPError as e:
        b = e.read()
        return e.code, (json.loads(b) if e.headers['Content-Type'] == 'application/json' else b)


def done(st):
    """How many completions are standing (st is the admin state)."""
    return st['completions']


def start(data):
    p = subprocess.Popen([sys.executable, os.path.join(HERE, 'server.py'), '--data', data, '--port', str(PORT),
                          '--host', '127.0.0.1', '--flush-interval', '0.5'],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    p.stdout.readline()                                  # wait for the startup message
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + '/api/state', timeout=1); break
        except Exception:
            time.sleep(0.1)
    return p


data = tempfile.mkdtemp(prefix='clipper-smoke-')
srv = start(data)
try:
    s, st = req('/api/state')
    check(s == 200 and st['phase'] == 'setup', 'a new game starts unset')
    s, r = req('/api/complete', {'id': 'red-0001', 'team': 'red', 'hood': 'North Beach', 'ci': 0, 'by': 'Maya'})
    check(s == 409, 'no completions before the game is set up')
    s, r = req('/api/admin/start-now', {})
    check(s == 200, 'the admin starts the game now')

    st0 = req('/api/admin/state')[1]['game']
    check(req('/api/admin/setup', {'start': st0['start'] + 60000, 'end': st0['end']})[0] == 409, 'the start is locked while the game is on')
    check(req('/api/admin/setup', {'end': st0['end'] + 60000})[0] == 200, '...but the end can still change')
    s, r = req('/api/complete', {'id': 'red-0001', 'team': 'red', 'hood': 'North Beach', 'ci': 0, 'by': 'Maya'})
    check(s == 200 and r['completion']['t'] > 0, 'Red completes North Beach #1 (server-stamped)')
    s, r2 = req('/api/complete', {'id': 'red-0001', 'team': 'red', 'hood': 'North Beach', 'ci': 0, 'by': 'Maya'})
    check(s == 200 and r2.get('retry'), 'retrying the same completion is harmless')
    s, r3 = req('/api/complete', {'id': 'red-0002', 'team': 'red', 'hood': 'North Beach', 'ci': 0, 'by': 'Jonah'})
    check(s == 409, 'a team cannot complete the same challenge twice')
    s, _ = req('/api/complete', {'id': 'bad', 'team': 'red', 'hood': 'Nowhere', 'ci': 0})
    check(s == 400, 'bad ids and unknown neighborhoods are rejected')

    NB = 'team=red&hood=North%20Beach&ci=0&by=Maya'
    for kind in ('full', 'web'):
        s, r = req(f'/api/photo?id=ph-red-01&{NB}&kind={kind}', raw=JPEG)
        check(s == 200, f'uploads the {kind} copy of a photo')
    s, _ = req(f'/api/photo?id=ph-red-02&{NB}&kind=full', raw=JPEG)
    check(s == 200, 'a second photo for the same challenge')
    check(req(f'/api/photo?id=ph-red-03&{NB}&kind=full', raw=b'not a jpeg')[0] == 400, 'non-JPEG uploads are rejected')
    s, st = req('/api/state?team=red')
    check(len([p for p in st['photos'] if p['hood'] == 'North Beach' and p['team'] == 'red']) == 2, 'both photos are listed')
    for i, ci in enumerate((1, 2)):
        s, _ = req('/api/complete', {'id': f'blue-000{i}', 'team': 'blue', 'hood': 'North Beach', 'ci': ci, 'by': 'Leo'})
        check(s == 200, f'Blue completes North Beach #{ci + 1}')

    sys.path.insert(0, HERE)
    from server import trios
    CH = trios(json.load(open(os.path.join(HERE, 'challenges.json'), encoding='utf-8')))
    one = next((h, i) for h, v in CH.items() for i, c in enumerate(v) if c['fail'] == 'one-shot')
    other = next((h, i) for h, v in CH.items() for i, c in enumerate(v) if c['fail'] != 'one-shot')
    s, _ = req('/api/fail', {'id': 'fail-0001', 'team': 'blue', 'hood': other[0], 'ci': other[1], 'by': 'Sam'})
    check(s == 409, 'only one-shot challenges can be marked as failed')
    s, f = req('/api/fail', {'id': 'fail-0002', 'team': 'blue', 'hood': one[0], 'ci': one[1], 'by': 'Sam'})
    check(s == 200 and f['fail']['t'] > 0, f'Blue fails the one-shot {one[0]} #{one[1] + 1}')
    s, _ = req('/api/complete', {'id': 'blue-0100', 'team': 'blue', 'hood': one[0], 'ci': one[1], 'by': 'Sam'})
    check(s == 409, '...and then cannot complete it')
    s, _ = req('/api/unfail', {'team': 'blue', 'hood': one[0], 'ci': one[1]})
    s, _ = req('/api/complete', {'id': 'blue-0101', 'team': 'blue', 'hood': one[0], 'ci': one[1], 'by': 'Sam'})
    check(s == 200, 'after undoing the failure (a misclick), Blue can complete it')
    s, _ = req('/api/uncomplete', {'team': 'blue', 'hood': one[0], 'ci': one[1]})
    s, f = req('/api/fail', {'id': 'fail-0003', 'team': 'blue', 'hood': one[0], 'ci': one[1], 'by': 'Sam'})
    check(s == 200, '...and switch back to failed')
    s, _ = req('/api/complete', {'id': 'red-0100', 'team': 'red', 'hood': one[0], 'ci': one[1], 'by': 'Maya'})
    check(s == 200, '...while Red still can')
    s, blue = req('/api/state?team=blue')
    check(len(blue['fails']) == 1 and blue['fails'][0]['team'] == 'blue', 'failures show in the game state')
    s, _ = req('/api/uncomplete', {'team': 'red', 'hood': one[0], 'ci': one[1]})
    s, blue = req('/api/state?team=blue')
    red = next(p for p in blue['photos'] if p['team'] == 'red')
    check(red['url'] is None, "during the game Blue can't see Red's photo")
    s, red_view = req('/api/state?team=red')
    url = next(p for p in red_view['photos'] if p['team'] == 'red')['url']
    check(req(url)[0] == 200, 'Red can see its own photo')
    check(req(url.replace('team=red', 'team=blue'))[0] == 403, "Blue can't fetch Red's photo by its address")

    before = req('/api/admin/state')[1]['log_writes']
    t0 = time.time()
    oks = []
    ths = [threading.Thread(target=lambda i=i: oks.append(req('/api/ping', {'team': 'red' if i % 2 else 'blue', 'by': 'x',
                                                                             'lat': 37.8 + i / 1e4, 'lon': -122.4})[0]))
           for i in range(30)]
    [t.start() for t in ths]; [t.join() for t in ths]
    after = req('/api/admin/state')[1]['log_writes']
    check(oks.count(200) == 30, '30 simultaneous location pings are all saved')
    check(after - before <= 4, f'...in {after - before} disk writes, not 30 (batched, {time.time() - t0:.1f}s)')
    for by, lat, lon in (('x', 37.9, -122.3), ('A', 37.7, -122.4), ('B', 37.8, -122.5)):
        req('/api/ping', {'team': 'red', 'by': by, 'lat': lat, 'lon': lon})
    sp = req('/api/state?team=blue')[1]['spots']
    check(sp['red']['players'] == 3 and abs(sp['red']['lat'] - 37.8) < 1e-9 and abs(sp['red']['lon'] + 122.4) < 1e-9
          and sp['blue']['players'] == 1, "everyone sees each team's spot: the average of its players' latest locations")

    # hard kill, then a damaged half-line at the end of the log, then restart
    srv.send_signal(signal.SIGKILL); srv.wait()
    with open(os.path.join(data, 'game.log'), 'a') as f:
        f.write('{"seq": 999, "type": "comp')
    srv = start(data)
    st = req('/api/admin/state')[1]
    check((done(st)) == 3 and st['pings'] == 33 and st['phase'] == 'playing',
          'after a hard kill and a damaged last line, the game is all there')
    s, r = req('/api/complete', {'id': 'red-0003', 'team': 'red', 'hood': 'Chinatown', 'ci': 1, 'by': 'Priya'})
    check(s == 200 and r['completion']['seq'] == st['seq'] + 1, 'play continues after the restart')

    srv.send_signal(signal.SIGTERM); srv.wait()
    srv = start(data)
    st2 = req('/api/admin/state')[1]
    check((done(st2)) == 4 and st2['seq'] == st['seq'] + 1, 'a second restart keeps the event saved after the damage')
    s, _ = req('/api/uncomplete', {'team': 'red', 'hood': 'Chinatown', 'ci': 1})
    check(s == 200 and (done(req('/api/admin/state')[1])) == 3, 'a team can undo its completion')
    s, _ = req('/api/uncomplete', {'team': 'red', 'hood': 'North Beach', 'ci': 0})
    s, _ = req('/api/complete', {'id': 'red-0004', 'team': 'red', 'hood': 'North Beach', 'ci': 0, 'by': 'Maya'})
    st = req('/api/state?team=red')[1]
    check(s == 200 and len([p for p in st['photos'] if p['hood'] == 'North Beach' and p['team'] == 'red']) == 2,
          'undoing and redoing a completion keeps its photos')
    s, _ = req('/api/photo/remove', {'photo': 'ph-red-02'})
    check(s == 200 and len([p for p in req('/api/state?team=red')[1]['photos'] if p['team'] == 'red']) == 1, 'a photo can be removed')
    s, _ = req('/api/uncomplete', {'team': 'blue', 'hood': 'North Beach', 'ci': 2})
    check(s == 200 and (done(req('/api/admin/state')[1])) == 2, 'Blue can undo too')

    check(req('/api/replay.json')[0] == 403, 'the finished game stays closed during the game')
    s, _ = req('/api/admin/end-now', {})
    st = req('/api/state?team=blue')[1]
    check(st['phase'] == 'over', 'the admin ends the game')
    check(req('/api/state?team=red')[1]['spots'] == {}, 'no live team spots once the game is over')
    check(req('/api/complete', {'id': 'blue-0009', 'team': 'blue', 'hood': 'Marina', 'ci': 0})[0] == 409, 'no completions after the end')
    red = next(p for p in st['photos'] if p['team'] == 'red')
    check(red['url'] and req(red['url'])[0] == 200, "after the game Blue can see Red's photo")

    # stop and start again: one game, and the replay covers every stretch
    first = req('/api/admin/state')[1]['game']['start']
    s, _ = req('/api/admin/start-now', {})
    s, r = req('/api/complete', {'id': 'blue-0200', 'team': 'blue', 'hood': 'Marina', 'ci': 0, 'by': 'Leo'})
    check(s == 200, 'after the end, Start again carries on the same game')
    s, _ = req('/api/admin/end-now', {})
    s, rj0 = req('/api/replay.json')
    check(rj0['game']['start'] == first and any(c['id'] == 'blue-0200' for c in rj0['game']['completions'])
          and any(c['id'] == 'red-0001' or c['hood'] == 'North Beach' for c in rj0['game']['completions']),
          'the replay starts at the first start and has both stretches')
    s, rj = req('/api/replay.json')
    check(s == 200 and len(rj['game']['completions']) == 3 and all(u.startswith('/photos/') for u in rj['photos'].values()),
          'after the game anyone can load the finished game')
    check(req('/api/export/photos.zip')[0] == 404, 'the downloads are only on the admin page')
    s, z = req('/api/admin/export/replay.zip')
    zf = zipfile.ZipFile(io.BytesIO(z))
    g = json.loads(zf.read('game.json'))
    check(g['format'] == 'clipper-conquest-replay' and len(g['completions']) == 3 and g['start'] and g['end'],
          'replay export: game.json in the replay format')
    check(len(g['fails']) == 1, 'replay export: failures included')
    nb = next(c for c in g['completions'] if c['hood'] == 'North Beach' and c['team'] == 'red')
    check(nb['photos'] == ['photos/ph-red-01.jpg'], 'replay export: each completion lists its photos')
    check('photos/ph-red-01.jpg' in zf.namelist() and len(g['pings']['red']) == 18 and 'Maya' in g['teams']['red']['players'],
          'replay export: photos, pings and players included')
    s, z = req('/api/admin/export/photos.zip')
    names = zipfile.ZipFile(io.BytesIO(z)).namelist()
    title = re.sub(r'<[^>]+>', '', CH['North Beach'][0]['title']).replace('&#x27;', "'")
    check(len(names) == 1 and re.fullmatch(r'Clipper Conquest photos/\d\d-\d\d Red - North Beach - ' + re.escape(title) + r' \(Maya\)\.jpg', names[0]),
          f'photo export names: {names[0]}')
    open(os.path.join(HERE, '.smoke-replay.ccreplay'), 'wb').write(req('/api/admin/export/replay.zip')[1])
    check(req('/admin')[0] == 200, 'the admin page opens without a key')
    req('/api/state?team=red&name=Maya')
    players = req('/api/admin/state')[1]['players']
    check(any(p['name'] == 'Maya' and p['team'] == 'red' and p['ago'] < 60e3 for p in players), "the admin page sees who's connected")
    check(req('/')[0] == 200, 'the app is served at /')
    check(all(req(u)[0] == 200 for u in ('/app.html', '/app.js', '/mobile.js', '/mobile.css', '/replay-core.js',
                                         '/challenges.json', '/sf_neighborhoods.geojson')),
          'the game app and everything it loads are served')
    check(all(req(u)[0] == 404 for u in ('/index.html', '/replay.html', '/rules-video.mp4', '/server.py', '/game-data/game.log',
                                         '/README.md', '/../server.py')),
          'nothing else is: not the guide or replay site, not the code, not the game data')
finally:
    srv.send_signal(signal.SIGTERM)
print(f'\nall {passed} checks passed (data in {data})')
