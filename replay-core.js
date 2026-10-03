/* Clipper Conquest: shared code for the guide, the game app and the replay site.
 *
 * A finished game is one plain JSON document plus its photos. The game server would write
 * exactly this at the end of a game; here a fake one is generated. Both the post-game app
 * (phone) and the static replay site (desktop) read it through the helpers below.
 *
 * game.json (format "clipper-conquest-replay", version 1):
 *   { format, version, title, start, end,                       // epoch ms
 *     teams: { red: {name:'Red', players:[...]}, blue: {name:'Blue', players:[...]} },
 *     challenges: { hood: [{title, where}, x3] },              // snapshot, so later edits don't change the replay
 *     completions: [{ id, t, team, hood, ci, by, photos }],    // photos = paths inside the pack, e.g. ['photos/p012.jpg']
 *     fails: [{ id, t, team, hood, ci, by, photos }],          // one-shots a team missed (they never change who holds what)
 *     pings: { red: [[t, lat, lon], ...], blue: [...] } }      // team locations over time
 *
 * A replay file (.ccreplay) is a zip of game.json + photos/. The public replay site opens it
 * entirely in the browser; nothing is uploaded.
 */
const CC = (() => {
  const TEAM = { red: 'Red', blue: 'Blue' };
  const COLOR = { red: '#C42847', blue: '#1D6FB8' };

  /* ---------- the challenges ---------- */
  // challenges.json holds every candidate; players see the first three per neighborhood, in
  // that order, with only these fields. Text is escaped for HTML, with **bold** / *italic* as tags.
  function md(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#x27;' }[c]))
      .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/(^|[^\w])\*([^*]+)\*(?!\w)/g, '$1<i>$2</i>');
  }
  function failKind(f) {
    f = (f || '').toLowerCase();
    return f.includes('one-shot') || f.includes('one shot') ? 'one-shot' : f.startsWith('retry') ? 'retryable' : '';
  }
  function trios(src) {           // { neighborhood: [3 challenges] } in map order
    const out = {};
    for (const [name, hood] of Object.entries(src)) {
      out[name] = hood.candidates.slice(0, 3).map(c => Object.assign(
        { title: md(c.title), do: md(c.do), where: md(c.where), fail: failKind(c.failable), photo: md(c.photo) },
        c.lat != null ? { lat: c.lat, lon: c.lon } : {},   // the exact spot, when it's been pinned
        c.place_id ? { placeId: c.place_id, placeName: c.place_name } : {}));   // its Google Maps place, when it has one
    }
    return out;
  }

  /* ---------- geometry ---------- */
  function ringCentroid(ring) {
    let a = 0, x = 0, y = 0;
    for (let i = 0; i < ring.length - 1; i++) {
      const [x1, y1] = ring[i], [x2, y2] = ring[i + 1], f = x1 * y2 - x2 * y1;
      a += f; x += (x1 + x2) * f; y += (y1 + y2) * f;
    }
    return a ? [x / (3 * a), y / (3 * a)] : ring[0];
  }
  function hoodCenters(geo) {           // name -> [lat, lon] of the largest ring's centroid
    const out = {};
    for (const f of geo.features) {
      const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
      const outer = polys.map(p => p[0]).sort((a, b) => b.length - a.length)[0];
      const [lon, lat] = ringCentroid(outer);
      out[f.properties.name] = [lat, lon];
    }
    return out;
  }
  const km = ([la1, lo1], [la2, lo2]) => {
    const R = 6371, d = Math.PI / 180, dl = (la2 - la1) * d, dn = (lo2 - lo1) * d;
    const h = Math.sin(dl / 2) ** 2 + Math.cos(la1 * d) * Math.cos(la2 * d) * Math.sin(dn / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(h));
  };

  /* ---------- a fake game ---------- */
  function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  // Two teams leave FiDi at 11:00 and play for five hours. Red tends to lock neighborhoods;
  // Blue zips around and goes after Red's, so neighborhoods change hands. Each team's
  // location is pinged every minute along the way.
  function fakeGame(geo, challenges, seed = 11) {
    const rand = rng(seed), C = hoodCenters(geo), names = Object.keys(C);
    const d0 = new Date(); d0.setHours(11, 0, 0, 0);
    const start = d0.getTime(), end = start + 5 * 3600e3, MIN = 60e3;
    const teams = { red: { name: 'Red', players: ['Maya', 'Jonah', 'Priya'] }, blue: { name: 'Blue', players: ['Leo', 'Sam', 'Ada'] } };
    const completions = [], fails = [], pings = { red: [], blue: [] };
    // Red tends to lock (2-3 challenges per stop); Blue zips (1-2) and hunts for steals.
    const plan = { red: { per: () => (rand() < 0.6 ? 3 : 2), pace: 1.0, steal: 0.2 },
                   blue: { per: () => (rand() < 0.6 ? 1 : 2), pace: 1.15, steal: 0.45 } };
    const T = { red: { here: 'Financial District/South Beach', t: start, seen: new Set() },
                blue: { here: 'Financial District/South Beach', t: start + 2 * MIN, seen: new Set() } };
    const ping = (team, a, b, t0, t1) => {                 // travel from a to b between t0 and t1, a ping a minute
      const bend = (rand() - 0.5) * 0.006, P = pings[team];
      for (let s = Math.ceil(t0 / MIN) * MIN; s <= t1; s += MIN) {
        const f = (s - t0) / Math.max(1, t1 - t0), w = Math.sin(Math.PI * f) * bend;
        P.push([s, +(a[0] + (b[0] - a[0]) * f + w + (rand() - 0.5) * 0.0004).toFixed(5),
                   +(a[1] + (b[1] - a[1]) * f - w + (rand() - 0.5) * 0.0004).toFixed(5)]);
      }
    };
    const holderNow = (hood, t) => {                      // who holds hood at time t, from completions so far
      let f = 0, s = 0, fl = 0, sl = 0;
      for (const c of completions) if (c.hood === hood && c.t <= t) { if (c.team === 'red') { f++; fl = c.t; } else { s++; sl = c.t; } }
      return !f && !s ? null : f !== s ? (f > s ? 'red' : 'blue') : (fl <= sl ? 'red' : 'blue');
    };
    const done = new Set();                               // "team|hood|ci"
    // Play the two teams in time order, one stop at a time, so each sees what the other has taken.
    while (T.red.t < end || T.blue.t < end) {
      const team = T.red.t <= T.blue.t ? 'red' : 'blue', me = T[team], other = team === 'red' ? 'blue' : 'red';
      me.seen.add(me.here);
      const todo = [0, 1, 2].filter(ci => !done.has(`${team}|${me.here}|${ci}`)).sort(() => rand() - 0.5).slice(0, plan[team].per());
      for (const ci of todo) {
        const t1 = me.t + (7 + rand() * 11) * MIN / plan[team].pace;
        ping(team, C[me.here], C[me.here], me.t, Math.min(t1, end));
        if (t1 > end) { me.t = end; break; }             // clock hit zero mid-challenge: it fails
        if ((challenges[me.here] || [])[ci]?.fail === 'one-shot' && rand() < 0.3) {   // missed a one-shot
          fails.push({ t: Math.round(t1), team, hood: me.here, ci, by: teams[team].players[Math.floor(rand() * 3)] });
          done.add(`${team}|${me.here}|${ci}`); me.t = t1 + (1 + rand() * 3) * MIN; continue;
        }
        completions.push({ t: Math.round(t1), team, hood: me.here, ci, by: teams[team].players[Math.floor(rand() * 3)] });
        done.add(`${team}|${me.here}|${ci}`);
        me.t = t1 + (1 + rand() * 3) * MIN;
      }
      if (me.t >= end) { me.t = end; continue; }
      const near = names.filter(x => x !== me.here && !me.seen.has(x)).sort((a, b) => km(C[me.here], C[a]) - km(C[me.here], C[b]));
      const theirs = near.slice(0, 8).filter(x => holderNow(x, me.t) === other);
      const pick = theirs.length && rand() < plan[team].steal ? theirs[0] : near.slice(0, 3)[Math.floor(rand() * Math.min(3, near.length))];
      if (!pick) { me.t = end; continue; }
      const t2 = Math.min(end, me.t + (4 + km(C[me.here], C[pick]) * (4.5 + rand() * 3)) * MIN);
      ping(team, C[me.here], C[pick], me.t, t2);
      me.here = pick; me.t = t2;
    }
    completions.sort((a, b) => a.t - b.t);
    let np = 0;
    const shots = n => Array.from({ length: n }, () => `photos/p${String(++np).padStart(3, '0')}.jpg`);
    completions.forEach((c, i) => { c.id = 'c' + String(i + 1).padStart(3, '0'); c.photos = shots(rand() < 0.65 ? 1 : 2 + Math.floor(rand() * 2)); });
    fails.sort((a, b) => a.t - b.t).forEach((f, i) => { f.id = 'f' + String(i + 1).padStart(3, '0'); f.photos = shots(rand() < 0.5 ? 0 : 1); });
    const snap = {};
    for (const [h, list] of Object.entries(challenges)) snap[h] = list.map(c => ({ title: c.title, where: c.where }));
    return { format: 'clipper-conquest-replay', version: 1, title: 'Clipper Conquest · demo game', start, end, teams,
             challenges: snap, completions, fails, pings };
  }

  /* ---------- who held what, when ---------- */
  // Same rule as the app: more completions holds it; a tie goes to whoever reached that count first.
  function tallyAt(game, T) {
    const tally = {};
    for (const c of game.completions) {
      if (c.t > T) break;
      const x = tally[c.hood] || (tally[c.hood] = { red: 0, blue: 0, redLast: 0, blueLast: 0 });
      x[c.team]++; x[c.team + 'Last'] = c.t;
    }
    for (const x of Object.values(tally))
      x.holder = x.red !== x.blue ? (x.red > x.blue ? 'red' : 'blue') : (x.redLast <= x.blueLast ? 'red' : 'blue');
    return tally;
  }
  function scoreAt(game, T) {
    const s = { red: 0, blue: 0 };
    for (const x of Object.values(tallyAt(game, T))) s[x.holder]++;
    return s;
  }
  // Each completion, annotated with the neighborhood's score after it, whether it changed hands,
  // and the overall score (neighborhoods held) after it.
  function events(game) {
    const tally = {}, out = [], held = { red: 0, blue: 0 };
    for (const c of game.completions) {
      const x = tally[c.hood] || (tally[c.hood] = { red: 0, blue: 0, holder: null });
      x[c.team]++;
      const holder = x.red !== x.blue ? (x.red > x.blue ? 'red' : 'blue') : x.holder || c.team;
      if (holder !== x.holder) { held[holder]++; if (x.holder) held[x.holder]--; }
      out.push({ ...c, red: x.red, blue: x.blue, change: holder !== x.holder ? (x.holder ? 'took' : 'claimed') : null, from: x.holder, score: { ...held } });
      x.holder = holder;
    }
    return out;
  }
  // Most neighborhoods at the end wins; tied, the team that first held that many wins.
  function winner(game) {
    const s = scoreAt(game, game.end);
    if (s.red !== s.blue) return { team: s.red > s.blue ? 'red' : 'blue', score: s, tie: false };
    const first = { red: Infinity, blue: Infinity };
    for (const c of game.completions) {
      const now = scoreAt(game, c.t);
      for (const k of ['red', 'blue']) if (now[k] >= s[k] && first[k] === Infinity) first[k] = c.t;
    }
    return { team: first.red <= first.blue ? 'red' : 'blue', score: s, tie: true };
  }
  function locationAt(game, team, T) {     // [lat, lon] or null, interpolated between pings
    const P = game.pings[team];
    if (!P.length || T < P[0][0]) return null;
    let lo = 0, hi = P.length - 1;
    if (T >= P[hi][0]) return [P[hi][1], P[hi][2]];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (P[m][0] <= T) lo = m; else hi = m; }
    const f = (T - P[lo][0]) / (P[hi][0] - P[lo][0]);
    return [P[lo][1] + (P[hi][1] - P[lo][1]) * f, P[lo][2] + (P[hi][2] - P[lo][2]) * f];
  }
  function trail(game, team, T, spanMs = 45 * 60e3) {
    return game.pings[team].filter(p => p[0] <= T && p[0] >= T - spanMs).map(p => [p[1], p[2]]);
  }

  // Every photo in the game: { path, entry (its completion or failure), n (its place in that list) }.
  function photoPaths(game) {
    const out = [];
    for (const e of [...game.completions, ...(game.fails || [])])
      (e.photos || (e.photo ? [e.photo] : [])).forEach((path, n) => out.push({ path, entry: e, n }));   // e.photo: older files
    return out.sort((a, b) => a.entry.t - b.entry.t || a.n - b.n);
  }
  const photosOf = e => e.photos || (e.photo ? [e.photo] : []);

  /* ---------- fake photos (canvas) ---------- */
  function fakePhoto(game, c, w = 960, h = 720, n = 0) {
    const cv = document.createElement('canvas'); cv.width = w; cv.height = h;
    const g = cv.getContext('2d'), col = COLOR[c.team];
    const sky = g.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, c.team === 'red' ? '#F3C6CF' : '#C5DBF0'); sky.addColorStop(1, col);
    g.fillStyle = sky; g.fillRect(0, 0, w, h);
    g.fillStyle = 'rgba(255,255,255,.18)';
    g.beginPath(); g.moveTo(0, h); g.bezierCurveTo(w * .3, h * .45, w * .55, h * .7, w, h * .38); g.lineTo(w, h); g.fill();
    g.beginPath(); g.arc(w * (.8 - n * .25), h * .22, h * .12, 0, 7); g.fill();
    g.fillStyle = '#fff'; g.textAlign = 'center';
    g.font = `800 ${Math.round(h * .075)}px system-ui, sans-serif`; g.fillText(c.hood, w / 2, h * .46);
    const title = (game.challenges[c.hood] || [])[c.ci];
    g.font = `500 ${Math.round(h * .045)}px system-ui, sans-serif`;
    g.fillText(title ? plain(title.title) : `Challenge ${c.ci + 1}`, w / 2, h * .56);
    g.font = `600 ${Math.round(h * .036)}px system-ui, sans-serif`; g.fillStyle = 'rgba(255,255,255,.85)';
    g.fillText(`${TEAM[c.team]} · ${c.by} · ${clock(c.t)}${n ? ` · photo ${n + 1}` : ''}`, w / 2, h * .9);
    return new Promise(r => cv.toBlob(r, 'image/jpeg', 0.82));
  }
  const plain = h => { const d = document.createElement('div'); d.innerHTML = h; return d.textContent; };
  const clock = t => new Date(t).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

  /* ---------- opening a replay file (made by the server's admin page) ---------- */
  // Returns { game, photos: {path: objectURL} }; throws if it isn't a replay file.
  async function openReplay(blob) {
    const zip = await JSZip.loadAsync(await blob.arrayBuffer());
    const game = JSON.parse(await zip.file('game.json').async('string'));
    if (game.format !== 'clipper-conquest-replay') throw new Error('not a replay file');
    const photos = {};
    for (const { path } of photoPaths(game)) {
      const f = zip.file(path);
      if (f) photos[path] = URL.createObjectURL(new Blob([await f.async('uint8array')], { type: 'image/jpeg' }));
    }
    return { game, photos };
  }
  // The demo: a fake game with fake photos.
  async function demo(geo, challenges) {
    const game = fakeGame(geo, challenges), photos = {};
    for (const { path, entry, n } of photoPaths(game)) photos[path] = URL.createObjectURL(await fakePhoto(game, entry, 960, 720, n));
    return { game, photos };
  }

  /* ---------- keep the last opened replay on this device (IndexedDB) ---------- */
  const idb = () => new Promise((res, rej) => { const r = indexedDB.open('cc-replay', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('files'); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  async function remember(blob) {
    try { const db = await idb(); db.transaction('files', 'readwrite').objectStore('files').put({ blob }, 'last'); } catch (e) {}
  }
  async function recall() {
    try { const db = await idb(); return await new Promise(res => { const r = db.transaction('files').objectStore('files').get('last');
      r.onsuccess = () => res(r.result || null); r.onerror = () => res(null); }); } catch (e) { return null; }
  }
  async function forget() { try { const db = await idb(); db.transaction('files', 'readwrite').objectStore('files').delete('last'); } catch (e) {} }

  // A Google Maps link for a challenge: the place's own page when it has a Place ID, else its exact
  // pin, else its address (the part before any "(…)" note or ";") searched in San Francisco.
  function mapsLink(c) {
    const base = 'https://www.google.com/maps/search/?api=1&query=';
    if (c.placeId) return base + encodeURIComponent(c.placeName) + '&query_place_id=' + encodeURIComponent(c.placeId);
    if (c.lat != null) return base + c.lat + ',' + c.lon;
    const d = document.createElement('p'); d.innerHTML = c.where || '';
    return base + encodeURIComponent(d.textContent.replace(/\s*\([^)]*\)/g, '').split(';')[0].trim() + ', San Francisco, CA');
  }

  return { trios, mapsLink, TEAM, COLOR, hoodCenters, fakeGame, fakePhoto, demo, photoPaths, photosOf, tallyAt, scoreAt, events, winner, locationAt, trail,
           openReplay, remember, recall, forget, clock, plain };
})();
