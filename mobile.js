/* The phone view, shared by the game app (app.html) and the replay site on phones
   (replay.html): the map, the Challenges and Timeline tabs, the clock, and the after-game
   replay (crown, time scrubber, team trails, downloads). A page loads mobile.css,
   replay-core.js and this file, then calls mountMobile(). The app adds app.js on top
   (talking to the game server); the replay site calls startMobileReplay() with a file. */

const MOBILE_HTML = `
<header>
  <div class="team red">
    <span class="dot" style="background:var(--red)"></span>
    <span class="label"><b>Red</b><span id="you-red"></span></span>
    <span class="count" id="score-red">0</span>
  </div>
  <div class="mid">
    <div class="clock" id="clock">–:––:––</div>
    <div class="clock-sub" id="clock-sub"></div>
    <div class="sync" id="sync" role="status"></div>
  </div>
  <div class="team blue">
    <span class="count" id="score-blue">0</span>
    <span class="label" style="text-align:right"><b>Blue</b><span id="you-blue"></span></span>
    <span class="dot" style="background:var(--blue)"></span>
  </div>
</header>

<div id="map-wrap">
  <svg id="map" role="list" aria-label="San Francisco neighborhoods"></svg>
</div>

<div id="timeline" aria-label="Game timeline"></div>
<section id="detail" aria-labelledby="det-name">
  <div id="panel">
    <div class="det-top">
      <span id="det-name"></span>
      <span id="det-pos"></span>
    </div>
    <div id="chal-track" aria-label="Challenges, swipe to browse"></div>
    <div id="dots" aria-hidden="true"></div>
  </div>
</section>

<footer>
  <div id="view-toggle" role="group" aria-label="View">
    <button id="view-map" aria-pressed="true">Map</button>
    <button id="view-challenges" aria-pressed="false">Challenges</button>
    <button id="view-timeline" aria-pressed="false">Timeline</button>
  </div>
  <button id="me" aria-label="Join the game">?</button>
</footer>

<div id="join" role="dialog" aria-modal="true" aria-labelledby="join-title">
  <div class="join-card">
    <h1 id="join-title">Clipper Conquest</h1>
    <p class="join-sub">Two teams, one afternoon, all of San Francisco.</p>
    <a class="join-guide" href="https://mwhittaker.github.io/clipper_conquest/" target="_blank" rel="noopener">
      <b>Read the guide</b><span>Rules, the rules video, the map and every challenge</span></a>
    <label class="join-label" for="join-name">Your name</label>
    <input id="join-name" type="text" autocomplete="off" maxlength="24" placeholder="e.g. Maya">
    <p class="join-label">Your team</p>
    <div class="join-teams">
      <button id="join-red" class="tbtn tf" aria-pressed="false">Red</button>
      <button id="join-blue" class="tbtn ts" aria-pressed="false">Blue</button>
    </div>
    <button id="join-go" disabled>Join the game</button>
    <p class="join-note">Change your name or team any time — tap your name under the map.
    Lose your connection or restart your phone? Just open the site again and you’re back in.</p>
  </div>
</div>

<input type="file" id="photo-in" accept="image/*" multiple hidden>

<dialog id="sheet" aria-labelledby="sheet-title"><div class="sheet-in">
  <h3 id="sheet-title"></h3>
  <p id="sheet-text"></p>
  <div class="sheet-body"></div>
  <div class="sheet-row"><button class="sheet-cancel"></button><button class="sheet-ok"></button></div>
</div></dialog>

<div id="lightbox" role="dialog" aria-modal="true" aria-label="Photo">
  <img id="lightbox-img" alt="">
  <div id="lightbox-cap"></div>
  <button id="lightbox-close" aria-label="Close photo">✕</button>
</div>
`;

const TEAM_NAME = { red: 'Red', blue: 'Blue' };

// state[hood] = [[redTime, blueTime] x3]: when each team completed each challenge (null = not yet).
// Holder = more completions; equal counts are broken by who got there first.
function fmt(t) {
  return new Date(t).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}
// The three playable challenges per neighborhood, keyed by name: CC.trios(challenges.json).
// Fields are escaped for HTML.
let CHALLENGES = {};
const MISSING = { title: 'Challenges didn’t load', do: 'Reload the page to try again.', where: '', photo: '', fail: null };
// The Where box: a pin, and the place, linked to Google Maps.
const PIN_SVG = '<svg class="pin" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.4"/></svg>';
function whereBox(c, cls) {
  const box = document.createElement('div');
  box.className = cls;
  box.innerHTML = PIN_SVG + `<p><b>Where</b><a class="maplink" target="_blank" rel="noopener">${c.where}</a></p>`;
  box.querySelector('.maplink').href = CC.mapsLink(c);   // the place's Google Maps page
  return box;
}
const FAIL_TEXT = { 'one-shot': ['oneshot', 'One shot'], retryable: ['retry', 'Retryable'], '': ['', 'Can’t fail'] };
function challengeFor(name, ci) { return (CHALLENGES[name] || [])[ci] || MISSING; }

let hoods = [];            // [{name, feature, path, badge}] sorted by name
let refreshLabels = () => {};   // set by buildMap; re-run on zoom or score changes
let mapZoomK = 1;               // current zoom (view width / full width)
let state = {};            // name -> [[redTime, blueTime] x3]
let profile = null;        // {name, team} in the app (saved on the phone); none in the replay site
let you = '';              // your team ('red' or 'blue') in the app
let current = -1;          // index into hoods for the open detail view

/* ---------- the game, as the server (or a replay file) describes it ----------
   The server holds the one shared game. This phone keeps who you are, plus an outbox of your
   team's changes and a queue of photos that haven't reached the server yet (saved on the phone,
   so a dropped signal or a reload loses nothing). The screen shows the server's game with the
   outbox on top. Every change carries its own id, so a retry never counts twice. */
let S = { phase: 'setup', game: {}, completions: [], fails: [], photos: [], seq: -1 };   // the last /api/state
let skew = 0;                        // the server's clock minus this phone's
const serverNow = () => Date.now() + skew;
let OVER = false;                    // the clock hit zero: everything is revealed and the map replays the game
let online = true;
const newId = p => `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

let fails = {};    // fails[hood][ci][team] = when that team marked the one-shot as failed
let photos = {};   // photos[hood][ci][team] = [{id, url, pending}]; url is null for the other team's until the end
function failedAt(name, ci, team) {
  return (fails[name] && fails[name][ci] && fails[name][ci][team]) || null;
}
function getPhotos(name, ci, team) {
  return (photos[name] && photos[name][ci] && photos[name][ci][team]) || [];
}
const photosFor = getPhotos;
function photoFor(name, ci, team) { const p = getPhotos(name, ci, team)[0]; return p ? p.url : null; }

// In the app, your team's changes and photos that haven't reached the server yet (app.js fills these).
let outbox = [];                 // [{op, body, t}]
const uploads = new Map();       // photo id -> {id, team, hood, ci, by, web, full, done, url}

// Rebuild what the screen shows: the server's game (up to time T, for the after-game replay),
// then this phone's unsent changes and photos on top.
function rebuild(T = Infinity) {
  state = {}; fails = {}; photos = {};
  hoods.forEach(h => { state[h.name] = [[null, null], [null, null], [null, null]]; });
  const slot = (obj, e) => ((obj[e.hood] = obj[e.hood] || {})[e.ci] = obj[e.hood][e.ci] || {});
  for (const c of S.completions) if (c.t <= T && state[c.hood]) state[c.hood][c.ci][c.team === 'red' ? 0 : 1] = c.t;
  for (const f of S.fails) if (f.t <= T) slot(fails, f)[f.team] = f.t;
  const removed = new Set(outbox.filter(o => o.op === 'photo_remove').map(o => o.body.photo));
  const add = (e, v) => { const x = slot(photos, e); (x[e.team] = x[e.team] || []).push(v); };
  for (const p of S.photos) if (!removed.has(p.id)) add(p, { id: p.id, url: p.url });
  for (const u of uploads.values()) add(u, { id: u.id, url: u.url, pending: !(u.done && u.done.web) });
  for (const o of outbox) {
    const b = o.body, row = state[b.hood] && state[b.hood][b.ci];
    if (!row) continue;
    const yi = b.team === 'red' ? 0 : 1;
    if (o.op === 'complete' && !row[yi]) row[yi] = o.t;
    if (o.op === 'uncomplete') row[yi] = null;
    if (o.op === 'fail') slot(fails, b)[b.team] = o.t;
    if (o.op === 'unfail' && fails[b.hood] && fails[b.hood][b.ci]) delete fails[b.hood][b.ci][b.team];
  }
}

// Anything that changes the game asks first, in a sheet that slides up from the bottom: what's
// about to happen, and what it means for the neighborhood. body: extra content under the text.
// Calling it again while it's open redraws it in place (the photo review adds and drops photos).
let sheetOpen = null;   // {onCancel, done} for the sheet on screen
function sheet({ title, text = '', body = null, ok, okClass = '', cancel = 'Cancel', onOk, onCancel = null }) {
  const d = document.getElementById('sheet');
  document.getElementById('sheet-title').textContent = title;
  const p = document.getElementById('sheet-text');
  p.textContent = text; p.hidden = !text;
  const box = d.querySelector('.sheet-body');
  box.textContent = '';
  if (body) box.append(...[].concat(body));
  const yes = d.querySelector('.sheet-ok'), no = d.querySelector('.sheet-cancel');
  yes.textContent = ok; yes.className = 'sheet-ok ' + okClass; yes.disabled = false;
  no.textContent = cancel;
  const me = sheetOpen = { onCancel, done: false };
  yes.onclick = () => { me.done = true; d.close(); onOk(); };
  no.onclick = () => d.close();
  if (!d.open) d.showModal();
  return d;
}
function sheetClosed() {             // Cancel, the backdrop, or the back gesture
  const s = sheetOpen;
  sheetOpen = null;
  if (s && !s.done && s.onCancel) s.onCancel();
}

// What completing (t = its time) or undoing (t = 0) a challenge would do to who holds the
// neighborhood, in a sentence: "Red takes Marina from Blue, 2–1."
function outcome(name, ci, team, t) {
  const before = hoodClass(name), saved = state[name];
  state[name] = saved.map((r, i) => i !== ci ? r : team === 'red' ? [t, r[1]] : [r[0], t]);
  const after = hoodClass(name), [r, b] = counts(name);
  state[name] = saved;
  const T = TEAM_NAME, lead = x => x === 'red' ? `${r}–${b}` : `${b}–${r}`;
  if (t) {
    if (before === 'open') return `${T[team]} claims ${name}.`;
    if (after !== team) return `${T[after]} still holds ${name}, ${lead(after)}.`;
    return before === team ? `${T[team]} holds ${name}, ${lead(team)}.` : `${T[team]} takes ${name} from ${T[before]}, ${lead(team)}.`;
  }
  if (before === team && after === 'open') return `${T[team]} would lose ${name}; nobody would hold it.`;
  if (before === team && after !== team) return `${T[team]} would lose ${name} to ${T[after]}, ${lead(after)}.`;
  return after === 'open' ? '' : `${T[after]} would still hold ${name}, ${lead(after)}.`;
}

function counts(name) {
  const rows = state[name];
  let red = 0, blue = 0;
  for (const [f, s] of rows) { if (f) red++; if (s) blue++; }
  return [red, blue];
}
function hoodClass(name) {
  const rows = state[name];
  let f = 0, s = 0, fLast = 0, sLast = 0;
  for (const [ft, st] of rows) {
    if (ft) { f++; fLast = Math.max(fLast, ft); }
    if (st) { s++; sLast = Math.max(sLast, st); }
  }
  if (!f && !s) return 'open';
  if (f !== s) return f > s ? 'red' : 'blue';
  return fLast <= sLast ? 'red' : 'blue';   // tie: whoever reached this count first
}

/* ---------- map ---------- */
// Short display names so labels fit on small polygons; anything not listed
// uses its full name. A label only shows once it fits at the current zoom.
const SHORT_NAMES = {
  'Bayview Hunters Point': 'Bayview',
  'Castro/Upper Market': 'Castro',
  'Financial District/South Beach': 'FiDi',
  'Golden Gate Park': 'GG Park',
  'Haight Ashbury': 'Haight',
  'Hayes Valley': 'Hayes',
  'Lone Mountain/USF': 'USF',
  'McLaren Park': 'McLaren',
  'Oceanview/Merced/Ingleside': 'OMI',
  'Pacific Heights': 'Pac Heights',
  'Presidio Heights': 'Presidio Hts',
  'Potrero Hill': 'Potrero',
  'South of Market': 'SoMa',
  'Sunset/Parkside': 'Sunset',
  'Treasure Island': 'Treasure Is',
  'Visitacion Valley': 'Vis Valley',
  'West of Twin Peaks': 'W Twin Peaks',
  'Western Addition': 'W Addition',
  'Bernal Heights': 'Bernal',
};

// Hand-tuned label nudges in map units ([dx, dy]), reviewed against a render.
const LABEL_TWEAKS = {
  'North Beach': [0, 10],
  'Golden Gate Park': [70, 0],
};

function project(features) {
  let minLon = 999, maxLon = -999, minLat = 999, maxLat = -999;
  const walk = (c, fn) => Array.isArray(c[0]) ? c.forEach(x => walk(x, fn)) : fn(c);
  features.forEach(f => walk(f.geometry.coordinates, ([lon, lat]) => {
    minLon = Math.min(minLon, lon); maxLon = Math.max(maxLon, lon);
    minLat = Math.min(minLat, lat); maxLat = Math.max(maxLat, lat);
  }));
  const kx = Math.cos((minLat + maxLat) / 2 * Math.PI / 180);
  const S = 1000 / ((maxLon - minLon) * kx);
  const W = 1000, H = (maxLat - minLat) * S;
  const pt = ([lon, lat]) => [(lon - minLon) * kx * S, (maxLat - lat) * S];
  return { pt, W, H };
}

// Longest horizontal run of land at height y, per ring (so a two-island
// neighborhood never gets a "chord" spanning the water between them).
function widestChordAt(rings, y) {
  let best = null;
  for (const pts of rings) {
    const xs = [];
    for (let i = 0; i < pts.length - 1; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
      if ((y1 <= y && y2 > y) || (y2 <= y && y1 > y)) {
        xs.push(x1 + (y - y1) * (x2 - x1) / (y2 - y1));
      }
    }
    xs.sort((a, b) => a - b);
    for (let i = 0; i + 1 < xs.length; i += 2) {
      const len = xs[i + 1] - xs[i];
      if (!best || len > best.len) best = { len, x: (xs[i] + xs[i + 1]) / 2 };
    }
  }
  return best;
}

function insideOuters(outers, x, y) {
  let cnt = 0;
  for (const pts of outers) {
    for (let i = 0; i < pts.length - 1; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
      if ((y1 <= y && y2 > y) || (y2 <= y && y1 > y)) {
        if (x < x1 + (y - y1) * (x2 - x1) / (y2 - y1)) cnt++;
      }
    }
  }
  return cnt % 2 === 1;
}

function centroid(ring) {
  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const cross = ring[i][0] * ring[i+1][1] - ring[i+1][0] * ring[i][1];
    a += cross; cx += (ring[i][0] + ring[i+1][0]) * cross; cy += (ring[i][1] + ring[i+1][1]) * cross;
  }
  return [cx / (3 * a), cy / (3 * a)];
}

function buildMap(geo) {
  const svg = document.getElementById('map');
  const NS = 'http://www.w3.org/2000/svg';
  const { pt, W, H } = project(geo.features);
  svg.setAttribute('viewBox', `0 0 ${W} ${H.toFixed(1)}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  const gPaths = document.createElementNS(NS, 'g');
  const gBadges = document.createElementNS(NS, 'g');
  svg.append(gPaths, gBadges);   // badges always draw above neighborhood fills

  // Measure label text with the same font it renders in (canvas works even
  // when the map is hidden behind the list view, unlike getComputedTextLength).
  const measCanvas = document.createElement('canvas');
  const meas = measCanvas.getContext && measCanvas.getContext('2d');
  if (meas) meas.font = '600 26px system-ui, sans-serif';
  const textWidth = s => meas ? meas.measureText(s).width : s.length * 26 * 0.56;

  geo.features
    .sort((a, b) => a.properties.name.localeCompare(b.properties.name))
    .forEach((f, i) => {
      const name = f.properties.name;
      const rings = f.geometry.type === 'Polygon' ? [f.geometry.coordinates]
                                                  : f.geometry.coordinates;
      let d = '', first = null, minY = 1e9, maxY = -1e9;
      const outers = [];   // outer ring of each polygon, projected
      rings.forEach(poly => poly.forEach((ring, ri) => {
        const pts = ring.map(pt);
        if (!first) first = pts;
        if (ri === 0) outers.push(pts);
        pts.forEach(p => { if (p[1] < minY) minY = p[1]; if (p[1] > maxY) maxY = p[1]; });
        d += 'M' + pts.map(p => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join('L') + 'Z';
      }));

      // Anchor label + badge on the widest strip of land that also has vertical
      // room for both rows — centroids drift outside on slanted or crescent
      // shapes, and the widest row alone can land on a thin arm (the Panhandle).
      const flat = (maxY - minY) < 60;
      const bdy = flat ? 8 : 17;
      // Score each row by width, discounted by distance from the vertical
      // center (0.47: the name+badge pair hangs slightly below its anchor).
      // A wide-but-high row only wins over a centered one when it is much
      // wider — this is what keeps tall rectangles like Sunset centered.
      const cand = [];
      for (let t = 0.18; t <= 0.82; t += 0.04) {
        const y = minY + (maxY - minY) * t;
        const c = widestChordAt(outers, y);
        if (c) cand.push({ ...c, y, score: c.len * (1 - 1.1 * Math.abs(t - 0.47)) });
      }
      cand.sort((a, b) => b.score - a.score);
      let anchor =
        cand.find(c => insideOuters(outers, c.x, c.y - 16) &&
                       insideOuters(outers, c.x, c.y + bdy + 4)) ||
        cand[0];
      if (!anchor) {
        const [cx, cy] = centroid(first);
        anchor = { x: cx, y: cy, len: 0 };
      }
      // Only 41 neighborhoods: hand-picked nudges (map units) beat cleverness
      // where the algorithm's choice reads slightly off. Reviewed visually.
      const tweak = LABEL_TWEAKS[name];
      if (tweak) anchor = { ...anchor, x: anchor.x + tweak[0], y: anchor.y + tweak[1] };
      const path = document.createElementNS(NS, 'path');
      path.setAttribute('d', d);
      path.setAttribute('tabindex', '0');
      path.setAttribute('role', 'listitem');
      path.setAttribute('aria-label', name);
      const open = () => showDetail(i);
      path.addEventListener('click', open);
      path.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
      gPaths.appendChild(path);

      // Flat strip-shaped neighborhoods can't fit a label row plus a badge
      // row — there the badge sits on the anchor row itself (bdy above). If
      // even that exits a tiny shape, walk the offset in until it's inside
      // (0 = on the anchor row, which is inside by construction).
      let dy = [bdy, 6, 4, 2, 0].find(v => insideOuters(outers, anchor.x, anchor.y + v));
      if (dy === undefined) dy = 0;
      const badge = document.createElementNS(NS, 'text');
      badge.setAttribute('x', anchor.x.toFixed(1));
      badge.setAttribute('y', (anchor.y + dy).toFixed(1));
      badge.setAttribute('class', 'badge');
      gBadges.appendChild(badge);

      const short = SHORT_NAMES[name] || name;
      const nameEl = document.createElementNS(NS, 'text');
      nameEl.setAttribute('x', anchor.x.toFixed(1));
      nameEl.setAttribute('y', (anchor.y - 5).toFixed(1));
      nameEl.setAttribute('class', 'hood-name');
      nameEl.textContent = short;
      gBadges.appendChild(nameEl);

      hoods.push({ name, path, badge, nameEl, short, flat,
                   ax: anchor.x, ay: anchor.y, ndy: 5, bdy: dy,
                   avail: anchor.len, textW: textWidth(short) });
    });

  // Show a neighborhood's label only when the measured name fits on the
  // widest strip of that neighborhood at the current zoom. On flat strips
  // with scores, the score badge takes the row and the label yields.
  // Text renders at a constant screen size while zooming, so the vertical
  // offsets from the anchor must scale with zoom exactly like the fonts do —
  // fixed map-unit offsets drift apart on screen as you zoom in.
  refreshLabels = () => {
    hoods.forEach(h => {
      const [f, s] = state[h.name] ? counts(h.name) : [0, 0];
      const fits = h.textW * mapZoomK < h.avail * 0.88;
      h.nameEl.classList.toggle('show', fits && !(h.flat && (f || s)));
      h.nameEl.setAttribute('y', (h.ay - h.ndy * mapZoomK).toFixed(1));
      h.badge.setAttribute('y', (h.ay + h.bdy * mapZoomK).toFixed(1));
    });
  };

  enableMapGestures(svg, W, H, k => { mapZoomK = k; refreshLabels(); });
}

/* ---------- map pan & pinch zoom ---------- */
function enableMapGestures(svg, W, H, onZoom) {
  const MAXZ = 8;
  let view = { x: 0, y: 0, w: W, h: H };
  const ptrs = new Map();
  let gesture = null;   // snapshot taken whenever the set of fingers changes
  let moved = 0;

  function apply() {
    view.w = Math.min(W, Math.max(W / MAXZ, view.w));
    view.h = view.w * H / W;
    view.x = Math.min(Math.max(view.x, 0), W - view.w);
    view.y = Math.min(Math.max(view.y, 0), H - view.h);
    svg.setAttribute('viewBox', `${view.x} ${view.y} ${view.w} ${view.h}`);
    const k = view.w / W;   // keep badges and labels the same size on screen at any zoom
    svg.style.setProperty('--badge-size', (22 * k) + 'px');
    svg.style.setProperty('--badge-stroke', (4 * k) + 'px');
    svg.style.setProperty('--name-size', (26 * k) + 'px');
    svg.style.setProperty('--name-stroke', (3.5 * k) + 'px');
    if (onZoom) onZoom(k);
  }

  // Rendered scale/offsets for preserveAspectRatio="meet".
  function fit(v) {
    const r = svg.getBoundingClientRect();
    const k = Math.min(r.width / v.w, r.height / v.h);
    return { r, k, ox: (r.width - v.w * k) / 2, oy: (r.height - v.h * k) / 2 };
  }
  function toMap(v, cx, cy) {
    const { r, k, ox, oy } = fit(v);
    return [v.x + (cx - r.left - ox) / k, v.y + (cy - r.top - oy) / k];
  }
  function anchor(mx, my, cx, cy) {   // position view so map point (mx,my) sits under client (cx,cy)
    const { r, k, ox, oy } = fit(view);
    view.x = mx - (cx - r.left - ox) / k;
    view.y = my - (cy - r.top - oy) / k;
  }

  function startGesture() {
    gesture = { view: { ...view }, ps: [...ptrs.values()].map(p => [...p]) };
  }
  svg.addEventListener('pointerdown', e => {
    ptrs.set(e.pointerId, [e.clientX, e.clientY]);
    if (ptrs.size === 1) moved = 0;
    startGesture();
  });
  svg.addEventListener('pointermove', e => {
    if (!ptrs.has(e.pointerId) || !gesture) return;
    ptrs.set(e.pointerId, [e.clientX, e.clientY]);
    const ps = [...ptrs.values()];
    if (ps.length === 1) {
      const [x0, y0] = gesture.ps[0], [x1, y1] = ps[0];
      moved = Math.max(moved, Math.hypot(x1 - x0, y1 - y0));
      const { k } = fit(gesture.view);
      view = { ...gesture.view, x: gesture.view.x - (x1 - x0) / k, y: gesture.view.y - (y1 - y0) / k };
      apply();
    } else {
      const [a0, b0] = gesture.ps, [a1, b1] = ps;
      moved = 999;
      const zoom = (Math.hypot(b1[0] - a1[0], b1[1] - a1[1]) || 1) /
                   (Math.hypot(b0[0] - a0[0], b0[1] - a0[1]) || 1);
      const m0 = [(a0[0] + b0[0]) / 2, (a0[1] + b0[1]) / 2];
      const m1 = [(a1[0] + b1[0]) / 2, (a1[1] + b1[1]) / 2];
      const [mx, my] = toMap(gesture.view, m0[0], m0[1]);
      view = { ...view, w: gesture.view.w / zoom, h: gesture.view.h / zoom };
      view.w = Math.min(W, Math.max(W / MAXZ, view.w));
      view.h = view.w * H / W;
      anchor(mx, my, m1[0], m1[1]);
      apply();
    }
  });
  const endPtr = e => {
    if (!ptrs.has(e.pointerId)) return;
    ptrs.delete(e.pointerId);
    if (ptrs.size) startGesture(); else gesture = null;
  };
  window.addEventListener('pointerup', endPtr);
  window.addEventListener('pointercancel', endPtr);

  // A drag or pinch must not count as a tap on a neighborhood.
  svg.addEventListener('click', e => {
    if (moved > 8) { e.stopPropagation(); e.preventDefault(); moved = 0; }
  }, true);

  function zoomAt(cx, cy, factor) {
    const [mx, my] = toMap(view, cx, cy);
    view.w = Math.min(W, Math.max(W / MAXZ, view.w / factor));
    view.h = view.w * H / W;
    anchor(mx, my, cx, cy);
    apply();
  }
  svg.addEventListener('dblclick', e => { e.preventDefault(); zoomAt(e.clientX, e.clientY, 2); });
  svg.addEventListener('wheel', e => { e.preventDefault(); zoomAt(e.clientX, e.clientY, Math.exp(-e.deltaY * 0.002)); }, { passive: false });

  if (onZoom) onZoom(1);   // initial label pass at full-city zoom
}

function paint() {
  let red = 0, blue = 0, open = 0;
  hoods.forEach(h => {
    const cls = hoodClass(h.name);
    h.path.setAttribute('class', cls);
    h.nameEl.classList.toggle('held', cls !== 'open');   // white on red or blue, dark on gray
    const [f, s] = counts(h.name);
    const active = Boolean(f || s);
    h.badge.textContent = active ? `${f}–${s}` : '';
    if (cls === 'red') red++; else if (cls === 'blue') blue++; else open++;
  });
  refreshLabels();
  document.getElementById('score-red').textContent = red;
  document.getElementById('score-blue').textContent = blue;
  renderTimeline();
  document.getElementById('you-red').textContent  = you === 'red'  ? ' (you)' : '';
  document.getElementById('you-blue').textContent = you === 'blue' ? ' (you)' : '';
}

/* ---------- detail view ---------- */
function showDetail(i, slideIdx = 0) {
  const wasOpen = document.body.classList.contains('chview');
  current = (i + hoods.length) % hoods.length;
  const name = hoods[current].name;
  try { localStorage.setItem('cc2-hood', name); } catch (e) {}
  const rows = state[name];
  const [f, s] = counts(name);

  document.getElementById('det-name').textContent = name;
  // Who holds it: the name in the holder's color. The score: Red–Blue, like the map's badges.
  const holderTeam = hoodClass(name);   // 'open' | 'red' | 'blue'
  const [w, l] = holderTeam === 'blue' ? [s, f] : [f, s];
  document.getElementById('det-name').className = holderTeam;
  const chip = document.getElementById('det-pos');
  chip.innerHTML = `<span class="cf">${f}</span>–<span class="cs">${s}</span>`;
  chip.className = holderTeam;
  chip.setAttribute('aria-label', holderTeam === 'open' ? 'Unclaimed, no completions yet'
    : `${TEAM_NAME[holderTeam]} holds it, ${w} to ${l}`);

  const track = document.getElementById('chal-track');
  const dots = document.getElementById('dots');
  track.textContent = '';
  dots.textContent = '';
  rows.forEach((row, ci) => {
    const slide = document.createElement('div');
    slide.className = 'slide';

    const c = challengeFor(name, ci);
    const [fcls, ftxt] = FAIL_TEXT[c.fail] || [];
    const which = document.createElement('div');
    which.className = 'c-head';
    which.innerHTML = `<span class="c-num" aria-hidden="true">${ci + 1}</span><div><h2></h2>` +
      (ftxt ? `<p class="c-fail ${fcls}">${ftxt}</p>` : '') + '</div>';
    which.querySelector('h2').innerHTML = c.title;
    const desc = document.createElement('p');
    desc.className = 'desc';
    desc.innerHTML = c.do;
    const metas = c.where ? [whereBox(c, 'where')] : [];

    const who = document.createElement('div');
    who.className = 'who';
    [['red', row[0]], ['blue', row[1]]].forEach(([key, time]) => {
      const failed = !time && failedAt(name, ci, key);
      const r = document.createElement('div');
      r.className = 'row' + (time ? ' done' : failed ? ' failed' : '');
      r.dataset.team = key;
      r.innerHTML = `<span class="dot" style="background:var(--${key})"></span>`;
      r.append(`${TEAM_NAME[key]} ${time ? '✓ completed ' + fmt(time) : failed ? '✗ failed ' + fmt(failed) : '— not yet'}`);
      who.appendChild(r);
    });

    const proofs = document.createElement('div');
    proofs.className = 'proofs';
    [['red', row[0]], ['blue', row[1]]].forEach(([key, time]) => {
      const list = photosFor(name, ci, key);
      if (!list.length) return;
      const visible = key === you || OVER;   // their photos might give the challenge away until the game ends
      const canEdit = key === you && !OVER && S.phase === 'playing';
      const own = list.length;
      const grp = document.createElement('figure');
      grp.className = 'pgroup';
      grp.dataset.team = key;
      const cap = document.createElement('figcaption');
      cap.textContent = `${list.length} photo${list.length > 1 ? 's' : ''}` + (visible ? '' : ' · hidden until the game ends');
      const strip = document.createElement('div');
      strip.className = 'pstrip';
      list.forEach((ph, i) => {
        const frame = document.createElement('span');
        frame.className = 'pframe';
        const im = document.createElement('img');
        if (!ph.url) {                         // the other team's, during the game: it exists, but no peeking
          frame.classList.add('hidden-photo');
          frame.setAttribute('aria-label', `${TEAM_NAME[key]}’s photo — hidden until the game ends`);
          strip.appendChild(frame);
          return;
        }
        im.src = ph.url;
        if (ph.pending) frame.classList.add('pending');
        if (visible) {
          im.alt = `${TEAM_NAME[key]}’s photo ${i + 1} — tap to enlarge`;
          im.setAttribute('role', 'button');
          im.setAttribute('tabindex', '0');
          const capText = `${TEAM_NAME[key]} · ${name} · photo ${i + 1} of ${list.length}`;
          im.addEventListener('click', () => openLightbox(ph.url, capText));
          im.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openLightbox(ph.url, capText); }
          });
        } else {
          im.classList.add('foe');
          im.alt = `${TEAM_NAME[key]}’s photo — hidden until the game ends`;
        }
        frame.appendChild(im);
        if (canEdit && i < own) {
          const del = document.createElement('button');
          del.className = 'pdel';
          del.textContent = '✕';
          del.setAttribute('aria-label', `Remove photo ${i + 1}`);
          del.onclick = () => {
            const big = document.createElement('div');
            big.className = 'sheet-big';
            big.innerHTML = '<img alt="">';
            big.firstChild.src = ph.url;
            sheet({ title: 'Remove this photo?', body: big, ok: 'Remove', okClass: 'danger', cancel: 'Keep',
                    onOk: () => { removePhoto(name, ci, key, i); afterChange(ci); } });
          };
          frame.appendChild(del);
        }
        strip.appendChild(frame);
      });
      grp.append(cap, strip);
      proofs.appendChild(grp);
    });

    const spacer = document.createElement('div');
    spacer.className = 'spacer';

    const btn = document.createElement('button');
    const yi = you === 'red' ? 0 : 1;
    const teamCls = you === 'red' ? 'redbtn' : 'bluebtn';
    const myFail = !row[yi] && failedAt(name, ci, you);
    const pick = complete => () => { photoTarget = { name, ci, complete }; photoIn.click(); };   // then app.js shows the photos to confirm
    const title = `“${CC.plain(c.title)}”`, other = TEAM_NAME[you === 'red' ? 'blue' : 'red'];
    const link = (text, cls = '') => { const b = document.createElement('button'); b.className = 'photo-act center ' + cls; b.textContent = text; return b; };
    const act = [];   // the smaller actions under the main button
    if (S.phase !== 'playing' && !OVER) {
      const st = S.game && S.game.start;
      btn.textContent = st && S.phase === 'before' ? `The game starts at ${fmt(st)}` : 'Waiting for the game to start';
      btn.className = 'undo';
      btn.disabled = true;
    } else if (row[yi]) {
      btn.textContent = 'Add photos';
      btn.className = 'undo ' + teamCls;
      btn.onclick = pick(false);
      const u = link('Undo the completion');
      u.onclick = () => sheet({ title: `Undo ${title}?`, text: `${outcome(name, ci, you, 0)} Your photos stay.`.trim(), ok: 'Undo',
                                onOk: () => { actUncomplete(name, ci); afterChange(ci); } });
      act.push(u);
    } else if (myFail) {
      btn.textContent = 'Failed. A one-shot can’t be retried.';
      btn.className = 'undo';
      btn.disabled = true;
      const u = link('Misclick? Undo the failure');
      u.onclick = () => sheet({ title: 'Undo the failure?', text: `You’ll be able to try ${title} again.`, ok: 'Undo',
                                onOk: () => { actUnfail(name, ci); afterChange(ci); } });
      const a = link('Add photos');
      a.onclick = pick(false);
      act.push(u, a);
    } else {
      // Photo proof is required: completing opens the camera / photo picker (one or several).
      btn.textContent = 'Complete with photo';
      btn.className = teamCls;
      btn.onclick = pick(true);
      // The bad-cell-signal backup: the completion counts now, the photos come later.
      const fb = link('Bad signal? Complete without a photo');
      fb.onclick = () => sheet({ title: `Complete ${title} without a photo?`,
                                 text: `${outcome(name, ci, you, Date.now() + skew)} You can add photos later.`, ok: 'Complete', okClass: teamCls,
                                 onOk: () => { actComplete(name, ci); afterChange(ci); } });
      act.push(fb);
      if (c.fail === 'one-shot') {
        const fl = document.createElement('button');   // as big as Complete: missing a one-shot is just as real
        fl.className = 'failbtn';
        fl.textContent = 'Missed it? Mark as failed';
        fl.onclick = () => sheet({ title: `Mark ${title} as failed?`, text: `A one-shot can’t be tried again. ${other} still can.`,
                                   ok: 'Mark failed', okClass: 'danger', onOk: () => { actFail(name, ci); afterChange(ci); } });
        act.unshift(fl);   // right under Complete
      }
    }

    // Each team in turn: its status, then its photos right under it.
    for (const grp of [...proofs.children]) who.querySelector(`.row[data-team="${grp.dataset.team}"]`).after(grp);
    slide.append(which, ...metas, desc, who);   // where first: it's what you need on the move
    slide.append(spacer);
    if (!OVER) { slide.appendChild(btn); act.forEach(b => slide.appendChild(b)); }
    track.appendChild(slide);

    const d = document.createElement('span');
    d.className = 'd' + (ci === slideIdx ? ' on' : '');
    dots.appendChild(d);
  });

  if (!wasOpen) setView('challenges');
  // Keep the browser's back button meaningful: arriving on the Challenges tab pushes
  // one history entry (so back = the view you came from); switching neighborhoods
  // there replaces it (so back still goes straight out).
  if (!navFromHistory) {
    const hash = '#' + encodeURIComponent(name);
    if (!wasOpen) history.pushState({ cc: 1 }, '', hash);
    else if (location.hash !== hash) history.replaceState({ cc: 1 }, '', hash);
  }
  requestAnimationFrame(() => {
    track.scrollLeft = slideIdx * track.clientWidth;
    updateDots();
  });
}

function updateDots() {
  const track = document.getElementById('chal-track');
  const cur = Math.round(track.scrollLeft / Math.max(1, track.clientWidth));
  document.querySelectorAll('#dots .d').forEach((d, i) => d.classList.toggle('on', i === cur));
}

function afterChange(slideIdx) {
  rebuild();
  paint();
  showDetail(current, slideIdx);
}

let navFromHistory = false;


/* ---------- full-screen photo viewer ---------- */
function openLightbox(src, cap) {
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox-cap').textContent = cap;
  document.getElementById('lightbox').classList.add('show');
}
function closeLightbox() {
  document.getElementById('lightbox').classList.remove('show');
}


/* ---------- timeline view ---------- */
// Every completion is an event. Replaying them in time order recovers the
// ownership story (claimed / took) with the same tie rule the map uses:
// on equal counts the previous holder keeps it, because they got there first.
function gameEvents() {
  const ev = [];
  hoods.forEach((h, hi) => {
    state[h.name].forEach((row, ci) => {
      if (row[0]) ev.push({ t: row[0], team: 'red', hi, ci });
      if (row[1]) ev.push({ t: row[1], team: 'blue', hi, ci });
    });
  });
  for (const [name, byCi] of Object.entries(fails)) {
    const hi = hoods.findIndex(h => h.name === name);
    if (hi < 0) continue;
    for (const [ci, byTeam] of Object.entries(byCi))
      for (const [team, t] of Object.entries(byTeam)) if (t) ev.push({ t, team, hi, ci: +ci, failed: true });
  }
  ev.sort((a, b) => a.t - b.t);
  const tally = {}, held = { red: 0, blue: 0 };   // held: the overall score
  for (const e of ev) {
    if (e.failed) continue;
    const name = hoods[e.hi].name;
    const t = tally[name] || (tally[name] = { f: 0, s: 0, holder: null });
    if (e.team === 'red') t.f++; else t.s++;
    let holder = t.f > t.s ? 'red' : t.s > t.f ? 'blue' : t.holder;
    if (!holder) holder = e.team;
    if (holder !== t.holder) {
      e.change = t.holder ? 'took' : 'claimed';
      held[holder]++; if (t.holder) held[t.holder]--;
      e.score = { ...held };
    }
    t.holder = holder;
    e.f = t.f; e.s = t.s;
  }
  return ev.reverse();   // newest first
}

function renderTimeline() {
  const tl = document.getElementById('timeline');
  tl.textContent = '';
  const ev = gameEvents();
  if (!ev.length) {
    const p = document.createElement('p');
    p.className = 'tl-empty';
    p.textContent = 'Nothing yet — completed challenges will show up here.';
    tl.appendChild(p);
    return;
  }
  ev.forEach(e => {
    const b = document.createElement('button');
    b.className = 'trow' + (e.change ? ' takeover' : '') + (e.failed ? ' failed' : '');
    const teamHTML = `<b class="${e.team === 'red' ? 'cf' : 'cs'}">${TEAM_NAME[e.team]}</b>`;
    let txt;
    if (e.failed) {
      txt = `${teamHTML} failed a challenge in <b class="hood"></b>`;
    } else if (e.change === 'claimed') {
      txt = `${teamHTML} claimed <b class="hood"></b>`;
    } else if (e.change === 'took') {
      const [w, l] = e.team === 'red' ? [e.f, e.s] : [e.s, e.f];
      txt = `${teamHTML} took <b class="hood"></b> ${w}–${l}`;
    } else {
      txt = `${teamHTML} completed a challenge in <b class="hood"></b>`;
    }
    const c = challengeFor(hoods[e.hi].name, e.ci);   // which challenge, like the desktop replay
    const score = e.change ? `<small class="tsc"><span class="cf">${e.score.red}</span>–<span class="cs">${e.score.blue}</span></small>` : '';   // the overall score, when it moves
    b.innerHTML = `<span class="tm">${fmt(e.t)}${score}</span><span class="tx">${txt}`
      + `<small class="tch">Challenge ${e.ci + 1}${c.title ? ' · ' + c.title : ''}</small></span>`;
    b.querySelector('.hood').textContent = hoods[e.hi].name;
    const list = e.failed ? [] : photosFor(hoods[e.hi].name, e.ci, e.team);
    if (list.length) {
      const frame = document.createElement('span');
      frame.className = 'tframe' + (list[0].url ? '' : ' hidden-photo');
      if (list[0].url) { const im = document.createElement('img'); im.src = list[0].url; im.alt = ''; frame.appendChild(im); }
      b.appendChild(frame);
    }
    b.onclick = () => showDetail(e.hi, e.ci);
    tl.appendChild(b);
  });
}

function setView(v) {
  if (!['map', 'challenges', 'timeline'].includes(v)) v = 'map';
  // The Challenges tab always shows a neighborhood: the last one looked at, else the first.
  if (v === 'challenges' && current < 0) {
    let last = null; try { last = localStorage.getItem('cc2-hood'); } catch (e) {}
    showDetail(Math.max(0, hoods.findIndex(h => h.name === last)));
    return;
  }
  document.body.classList.toggle('chview', v === 'challenges');
  document.body.classList.toggle('tlview', v === 'timeline');
  ['map', 'challenges', 'timeline'].forEach(k =>
    document.getElementById('view-' + k).setAttribute('aria-pressed', String(v === k)));
  try { localStorage.setItem('cc2-view', v); } catch (e) {}
  // leaving the Challenges tab: drop the #neighborhood from the address, so a refresh stays here
  if (v !== 'challenges' && location.hash) history.replaceState(null, '', location.pathname + location.search);
  if (OVER) showAt(PGT);
}

/* ---------- clock ---------- */
// Counts down to the start, then to the end, on the server's clock. After the game, the map
// tab shows the time left at the moment you've scrubbed to.
function tick() {
  const g = S.game || {}, now = serverNow(), sub = document.getElementById('clock-sub');
  let ms = null, label = '';
  if (OVER) { ms = document.body.classList.contains('chview') || document.body.classList.contains('tlview') ? 0 : g.end - PGT; label = ms > 0 ? 'left' : 'Final'; }
  else if (S.phase === 'before') { ms = g.start - now; label = 'until the game starts'; }
  else if (S.phase === 'playing') { ms = g.end - now; label = 'left'; }
  else if (S.phase === 'over') { ms = 0; label = 'Final'; }
  else label = 'Waiting for the start time';
  const el = document.getElementById('clock');
  if (ms === null) el.textContent = '–:––:––';
  else {
    ms = Math.max(0, ms);
    const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60;
    el.textContent = `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  }
  sub.textContent = label;
  if (!OVER && ((S.phase === 'playing' && g.end && now >= g.end) || (S.phase === 'before' && g.start && now >= g.start))
      && typeof poll === 'function') poll();   // it's time: pick up the start or the end right away
}

/* ---------- after the game ----------
   When the server says the game is over (or you open a replay file with no server around),
   the app becomes the replay: both teams' photos show, nothing can be changed, the winner's
   dot gets a crown, and the map tab gets a time scrubber with each team's route. */
let REPLAY = null, PGT = 0, GEO = null;
function fromReplay(r) {        // the finished game in the same shape as /api/state
  const g = r.game, flat = [];
  for (const e of [...g.completions, ...(g.fails || [])])
    CC.photosOf(e).forEach(path => flat.push({ id: path, t: e.t, team: e.team, hood: e.hood, ci: e.ci, url: r.photos[path] || null }));
  return { phase: 'over', seq: -1, game: { title: g.title, start: g.start, end: g.end },
           completions: g.completions, fails: g.fails || [], photos: flat };
}
async function startReplay(r) {
  if (!r) {
    const res = await fetch('api/replay.json', { cache: 'no-store' });
    r = await res.json();
  }
  REPLAY = r;
  S = fromReplay(r);
  OVER = true;
  document.body.classList.add('pg');
  buildScrubber(); buildTeams(); addCrown(); buildSheet();
  showAt(S.game.end);
  if (current >= 0) showDetail(current);
}
function onMap() { return !document.body.classList.contains('chview') && !document.body.classList.contains('tlview'); }
function showAt(T) {
  PGT = Math.max(S.game.start, Math.min(S.game.end, T));
  rebuild(onMap() ? PGT : Infinity);
  paint(); drawTeams(); tick();
  const r = document.getElementById('sc-range');
  if (r) { r.value = PGT; document.getElementById('sc-time').textContent = CC.clock(PGT); }
}

let playing = null;
function buildScrubber() {
  const g = S.game, bar = document.createElement('div');
  bar.id = 'scrub';
  bar.innerHTML = `<button id="sc-play" aria-label="Play the game back">▶</button>
    <div class="sc-track"><div class="sc-ticks"></div>
      <input type="range" id="sc-range" min="${g.start}" max="${g.end}" step="1000" aria-label="Time"></div>
    <span id="sc-time"></span>`;
  document.querySelector('footer').before(bar);
  const ticks = bar.querySelector('.sc-ticks');   // a tick each time a neighborhood changed hands
  for (const e of CC.events(REPLAY.game)) if (e.change) {
    const i = document.createElement('i');
    i.style.left = (100 * (e.t - g.start) / (g.end - g.start)) + '%';
    i.style.background = CC.COLOR[e.team];
    ticks.appendChild(i);
  }
  const range = bar.querySelector('#sc-range'), play = bar.querySelector('#sc-play');
  const stop = () => { if (playing) cancelAnimationFrame(playing); playing = null; play.textContent = '▶'; play.setAttribute('aria-label', 'Play the game back'); };
  range.addEventListener('input', () => { stop(); showAt(+range.value); });
  play.onclick = () => {
    if (playing) return stop();
    if (PGT >= g.end) showAt(g.start);
    play.textContent = '❚❚'; play.setAttribute('aria-label', 'Pause');
    let last = performance.now(), acc = 0;
    const SPEED = (g.end - g.start) / 45e3;          // the whole game in about 45 seconds
    const step = now => {
      const dt = now - last; last = now; acc += dt;
      PGT = Math.min(g.end, PGT + dt * SPEED);
      if (acc > 60 || PGT >= g.end) { acc = 0; showAt(PGT); }
      if (PGT >= g.end) return stop();
      playing = requestAnimationFrame(step);
    };
    playing = requestAnimationFrame(step);
  };
}

let teamLayer = null, P = null;
function buildTeams() {             // each team's dot (and after the game, its route)
  if (teamLayer) return;
  const NS = 'http://www.w3.org/2000/svg', svg = document.getElementById('map');
  P = project(GEO.features).pt;
  teamLayer = document.createElementNS(NS, 'g');
  teamLayer.id = 'teams';
  for (const team of ['red', 'blue']) {
    const line = document.createElementNS(NS, 'polyline');
    line.setAttribute('class', 'trail ' + team);
    const dot = document.createElementNS(NS, 'circle');
    dot.setAttribute('class', 'tdot ' + team); dot.setAttribute('r', 17);
    teamLayer.append(line, dot);
  }
  svg.appendChild(teamLayer);
}
function drawTeams() {
  if (!teamLayer) return;
  for (const team of ['red', 'blue']) {
    // During the game: where the server says the team is (its players' average, shown to everyone).
    const spot = !OVER && S.spots && S.spots[team];
    const here = OVER ? (onMap() ? CC.locationAt(REPLAY.game, team, PGT) : null) : spot ? [spot.lat, spot.lon] : null;
    const dot = teamLayer.querySelector('.tdot.' + team), line = teamLayer.querySelector('.trail.' + team);
    if (!here) { dot.style.display = 'none'; line.setAttribute('points', ''); continue; }
    const [x, y] = P([here[1], here[0]]);
    dot.style.display = ''; dot.setAttribute('cx', x.toFixed(1)); dot.setAttribute('cy', y.toFixed(1));
    if (!OVER) { line.setAttribute('points', ''); continue; }
    const pts = CC.trail(REPLAY.game, team, PGT).map(([la, lo]) => P([lo, la]).map(v => v.toFixed(1)).join(','));
    line.setAttribute('points', pts.concat(`${x.toFixed(1)},${y.toFixed(1)}`).join(' '));
  }
}

const CROWN = '<svg class="crown" viewBox="0 0 24 18" aria-hidden="true"><path d="M2 15 1 4l6 5 5-8 5 8 6-5-1 11z"/><rect x="2" y="15.5" width="20" height="2.5" rx="1"/></svg>';
function addCrown() {                                // perched on the winning team's dot
  const w = CC.winner(REPLAY.game), dot = document.querySelector(`header .team.${w.team} .dot`);
  dot.classList.add('crowned');
  dot.insertAdjacentHTML('beforeend', CROWN);
  dot.parentElement.setAttribute('title', `${TEAM_NAME[w.team]} won${w.tie ? ' on the tiebreak' : ''}`);
}

// The sheet behind your badge: the result and the downloads.
function buildSheet() {                // the result (the downloads are on the admin page)
  const g = REPLAY.game, w = CC.winner(g), s = w.score;
  const [a, b] = w.team === 'red' ? ['red', 'blue'] : ['blue', 'red'];
  const sec = document.createElement('section');
  sec.className = 'pg-over';
  sec.innerHTML = `
    <p class="pg-eyebrow">Game over · ${new Date(g.start).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}</p>
    <h2>${CROWN}${TEAM_NAME[w.team]} wins <span class="${a === 'red' ? 'cf' : 'cs'}">${s[a]}</span>–<span class="${b === 'red' ? 'cf' : 'cs'}">${s[b]}</span></h2>
    ${w.tie ? '<p class="pg-note">Tied on neighborhoods; they got there first.</p>' : ''}
    <p class="pg-note">${g.completions.length} challenges completed, ${CC.photoPaths(g).length} photos.</p>
    ${REPLAY.file ? '<button class="pg-link" id="pg-open">Open another replay file…</button>' : ''}
    <button class="pg-btn ghost" id="pg-close">Close</button>`;
  document.querySelector('.join-card').prepend(sec);
  const open = sec.querySelector('#pg-open');
  if (open) open.onclick = () => { CC.forget(); location.reload(); };
  sec.querySelector('#pg-close').onclick = () => document.getElementById('join').classList.remove('show');
}

// Put the phone view on the page and wire it up. The app calls this first thing; the replay
// site calls it when it's opened on a phone.
function mountMobile() {
  document.body.insertAdjacentHTML('afterbegin', MOBILE_HTML);
  document.getElementById('chal-track').addEventListener('scroll', updateDots, { passive: true });
  document.getElementById('lightbox').addEventListener('click', closeLightbox);
  document.getElementById('lightbox-close').addEventListener('click', closeLightbox);
  const sh = document.getElementById('sheet');
  sh.addEventListener('close', sheetClosed);
  sh.addEventListener('click', e => { if (e.target === sh) sh.close(); });   // a tap on the dimmed page cancels
  document.getElementById('view-map').onclick = () => setView('map');
  document.getElementById('view-challenges').onclick = () => setView('challenges');
  document.getElementById('view-timeline').onclick = () => setView('timeline');
  window.addEventListener('popstate', e => {
    if (e.state && e.state.cc) {
      const name = decodeURIComponent(location.hash.slice(1));
      const i = hoods.findIndex(h => h.name === name);
      if (i >= 0) { navFromHistory = true; showDetail(i); navFromHistory = false; }
    } else if (document.body.classList.contains('chview')) {
      setView('map');
    }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && document.getElementById('lightbox').classList.contains('show')) {
      closeLightbox();
      return;
    }
    if (!document.body.classList.contains('chview')) return;
    const track = document.getElementById('chal-track');
    if (e.key === 'ArrowLeft') track.scrollBy({ left: -track.clientWidth, behavior: 'smooth' });
    if (e.key === 'ArrowRight') track.scrollBy({ left: track.clientWidth, behavior: 'smooth' });
    if (e.key === 'Escape') setView('map');
  });
  setInterval(tick, 1000);
}

// The replay site on a phone: show a finished game from a replay file.
async function startMobileReplay(r, geo, trios) {
  CHALLENGES = trios;
  GEO = geo;
  buildMap(geo);
  await startReplay({ ...r, file: true });
  setView('map');
  const me = document.getElementById('me');   // the badge opens the result and the downloads
  me.textContent = '☰';
  me.setAttribute('aria-label', 'The result');
  me.onclick = () => document.getElementById('join').classList.add('show');
}
