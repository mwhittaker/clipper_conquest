/* The game app's live side: everything that talks to the game server. The phone view
   itself (map, tabs, replay) is mobile.js, loaded first.

   The server holds the one shared game. This phone keeps who you are, plus an outbox of
   your team's changes and a queue of photos that haven't reached the server yet (saved on
   the phone, so a dropped signal or a reload loses nothing). Every change carries its own
   id, so a retry never counts twice. */

mountMobile();
try { profile = JSON.parse(localStorage.getItem('cc2-profile') || 'null'); } catch (e) {}
if (profile && { fog: 1, surf: 1 }[profile.team]) profile.team = profile.team === 'fog' ? 'red' : 'blue';   // saved before the rename
you = (profile && profile.team) || 'red';

/* ----- the outbox: your team's changes, sent in order ----- */
try { outbox = JSON.parse(localStorage.getItem('cc2-outbox') || '[]'); } catch (e) {}
const saveOutbox = () => { try { localStorage.setItem('cc2-outbox', JSON.stringify(outbox)); } catch (e) {} };
function send(op, body) {
  outbox.push({ op, body: { ...body, team: you, by: profile ? profile.name : '' }, t: serverNow() });
  saveOutbox();
  flush();
}

/* ----- the photo queue: kept in the phone's IndexedDB until uploaded ----- */
const upDB = () => new Promise((res, rej) => {
  const r = indexedDB.open('cc2-uploads', 1);
  r.onupgradeneeded = () => r.result.createObjectStore('u');
  r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
});
async function upPut(u) { try { const { url, ...rest } = u; (await upDB()).transaction('u', 'readwrite').objectStore('u').put(rest, u.id); } catch (e) {} }
async function upDel(id) { try { (await upDB()).transaction('u', 'readwrite').objectStore('u').delete(id); } catch (e) {} }
async function upLoad() {
  try {
    const db = await upDB();
    const all = await new Promise(res => { const q = db.transaction('u').objectStore('u').getAll(); q.onsuccess = () => res(q.result || []); q.onerror = () => res([]); });
    for (const u of all) uploads.set(u.id, { ...u, url: URL.createObjectURL(u.web) });
  } catch (e) {}
}

// Send the outbox, then the photos. A server or network error stops and retries shortly;
// anything the server refuses (say, the game just ended) is dropped with a message.
let flushing = false;
async function flush() {
  if (flushing) return;
  flushing = true;
  try {
    while (outbox.length) {
      const o = outbox[0];
      const r = await fetch('api/' + (o.op === 'photo_remove' ? 'photo/remove' : o.op),
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(o.body) });
      if (r.status >= 500) throw new Error('server');
      if (!r.ok) toast((await r.json().catch(() => ({}))).error || 'That didn’t go through.');
      outbox.shift(); saveOutbox();
    }
    for (const u of [...uploads.values()]) {
      for (const kind of ['web', 'full']) {           // the small copy first, so it shows up quickly
        if (u.done && u.done[kind]) continue;
        const q = new URLSearchParams({ id: u.id, team: u.team, hood: u.hood, ci: u.ci, by: u.by, kind });
        const r = await fetch('api/photo?' + q, { method: 'POST', headers: { 'Content-Type': 'image/jpeg' }, body: u[kind] });
        if (r.status >= 500) throw new Error('server');
        if (!r.ok) { toast((await r.json().catch(() => ({}))).error || 'A photo didn’t upload.'); break; }
        u.done = { ...(u.done || {}), [kind]: true };
        upPut(u);
      }
      uploads.delete(u.id); upDel(u.id);
    }
    online = true;
  } catch (e) {
    online = false;
    setTimeout(flush, 4000);
  } finally {
    flushing = false;
    showSync();
  }
  poll();
}

// Ask the server what's new (every 5 s, or 20 s while the app is in the background).
let pollTimer = null;
async function poll() {
  clearTimeout(pollTimer);
  try {
    const t0 = Date.now();
    const r = await fetch('api/state?team=' + encodeURIComponent(you) + '&name=' + encodeURIComponent(profile ? profile.name : ''), { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    const next = await r.json();
    skew = next.now - (t0 + Date.now()) / 2;
    online = true;
    if (OVER) {                  // the replay is showing: keep it (it covers every stretch), just watch for a restart
      if (next.phase !== 'over') return location.reload();   // the organizer started again
    } else {
      const changed = next.seq !== S.seq || next.phase !== S.phase;
      S = next;
      if (S.phase === 'over') { await startReplay(); pollTimer = setTimeout(poll, 5000); return; }
      if (changed) refresh();
      drawTeams();               // the teams' spots move without other changes
    }
  } catch (e) { online = false; }
  showSync();
  pollTimer = setTimeout(poll, document.hidden ? 20000 : 5000);   // after the game too, to catch a restart
}
document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });

// Redraw with the latest game, keeping your place in the Challenges tab.
function refresh() {
  rebuild();
  paint();
  if (document.body.classList.contains('chview') && current >= 0) {
    const track = document.getElementById('chal-track');
    const at = Math.round(track.scrollLeft / Math.max(1, track.clientWidth));
    const tops = [...track.children].map(sl => sl.scrollTop);
    showDetail(current, at);
    [...track.children].forEach((sl, i) => { sl.scrollTop = tops[i] || 0; });
  }
}

function showSync() {
  const n = outbox.length + uploads.size, el = document.getElementById('sync');
  el.textContent = !online ? `Offline${n ? ` · ${n} waiting to send` : ''}` : n ? `Sending ${n}…` : '';
  el.className = 'sync' + (!online ? ' off' : '');
}
let toastTimer = null;
function toast(msg) {
  const el = document.getElementById('sync');
  el.textContent = msg; el.className = 'sync off';
  clearTimeout(toastTimer); toastTimer = setTimeout(showSync, 5000);
}

/* ----- your team's actions ----- */
function actComplete(name, ci) { send('complete', { id: newId('c'), hood: name, ci }); }
function actUncomplete(name, ci) { send('uncomplete', { hood: name, ci }); }
function actFail(name, ci) { send('fail', { id: newId('f'), hood: name, ci }); }
function actUnfail(name, ci) { send('unfail', { hood: name, ci }); }
function removePhoto(name, ci, team, i) {
  const ph = getPhotos(name, ci, team)[i];
  if (!ph) return;
  if (uploads.has(ph.id)) { uploads.delete(ph.id); upDel(ph.id); showSync(); }
  else send('photo_remove', { photo: ph.id });
}

// Location: phones only share it with secure (HTTPS) pages, so the app only asks there.
// One ping a minute while the app is open and the game is on. Everyone's map shows each team's
// spot (the average of its players' latest pings); the routes show in the replay.
function startPings() {
  if (!window.isSecureContext || !navigator.geolocation) return;
  const ping = () => {
    if (S.phase !== 'playing' || !profile || document.hidden) return;
    navigator.geolocation.getCurrentPosition(pos => {
      fetch('api/ping', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ team: you, by: profile.name, lat: pos.coords.latitude, lon: pos.coords.longitude }) }).catch(() => {});
    }, () => {}, { maximumAge: 30000, timeout: 20000 });
  };
  ping();
  setInterval(ping, 60000);
}

let photoTarget = null;   // {name, ci, complete} awaiting a file pick
const photoIn = document.getElementById('photo-in');
// Each photo goes up twice: a small copy (1600px) for the app, then the original for the album.
function jpeg(file, max, q) {
  return new Promise(res => {
    const img = new Image();
    img.onload = () => {
      const k = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement('canvas');
      c.width = Math.round(img.width * k);
      c.height = Math.round(img.height * k);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(img.src);
      c.toBlob(res, 'image/jpeg', q);
    };
    img.onerror = () => res(null);
    img.src = URL.createObjectURL(file);
  });
}
// Picked photos wait in a sheet to be checked (drop one, add more) before anything is sent.
let review = null;   // {name, ci, complete, files: [{file, url}]} while that sheet is open
photoIn.onchange = () => {
  const files = [...photoIn.files];
  photoIn.value = '';
  const t = photoTarget;
  photoTarget = null;
  if (!files.length || !t) return;
  if (!review || review.name !== t.name || review.ci !== t.ci) review = { ...t, files: [] };
  review.files.push(...files.map(file => ({ file, url: URL.createObjectURL(file) })));
  showReview();
};
function showReview() {
  const r = review, c = challengeFor(r.name, r.ci), title = `“${CC.plain(c.title)}”`;
  const completing = r.complete && !state[r.name][r.ci][you === 'red' ? 0 : 1];
  const grid = document.createElement('div');
  grid.className = 'sheet-photos';
  r.files.forEach((f, i) => {
    const fr = document.createElement('div'), im = document.createElement('img'), x = document.createElement('button');
    fr.className = 'sp';
    im.src = f.url; im.alt = `Photo ${i + 1}`;
    x.textContent = '✕'; x.setAttribute('aria-label', `Drop photo ${i + 1}`);
    x.onclick = () => { URL.revokeObjectURL(f.url); r.files.splice(i, 1); showReview(); };
    fr.append(im, x);
    grid.appendChild(fr);
  });
  const add = document.createElement('button');
  add.className = 'add'; add.textContent = '+ Add';
  add.setAttribute('aria-label', 'Add more photos');
  add.onclick = () => { photoTarget = { name: r.name, ci: r.ci, complete: r.complete }; photoIn.click(); };
  grid.appendChild(add);
  const n = r.files.length;
  const d = sheet({
    title: completing ? `Complete ${title}?` : `Add ${n === 1 ? 'this photo' : `these ${n} photos`} to ${title}?`,
    text: completing ? outcome(r.name, r.ci, you, Date.now() + skew) : '',
    body: grid, ok: completing ? 'Complete' : 'Add photos', okClass: you === 'red' ? 'redbtn' : 'bluebtn',
    onOk: sendReview, onCancel: dropReview,
  });
  d.querySelector('.sheet-ok').disabled = !n;
}
function dropReview() {
  if (review) review.files.forEach(f => URL.revokeObjectURL(f.url));
  review = null;
}
async function sendReview() {
  const t = review;
  review = null;
  if (t.complete && !state[t.name][t.ci][you === 'red' ? 0 : 1]) { actComplete(t.name, t.ci); afterChange(t.ci); }   // counts now; photos follow
  for (const { file: f, url } of t.files) {
    URL.revokeObjectURL(url);
    const [web, full] = await Promise.all([jpeg(f, 1600, 0.82), f.type === 'image/jpeg' ? f : jpeg(f, 1e5, 0.92)]);
    if (!web || !full) { toast('That photo couldn’t be read.'); continue; }
    const u = { id: newId('p'), team: you, hood: t.name, ci: t.ci, by: profile ? profile.name : '', web, full, done: {} };
    uploads.set(u.id, { ...u, url: URL.createObjectURL(web) });
    upPut(u);
  }
  afterChange(t.ci);
  flush();
}

/* ---------- join / profile ---------- */
let joinTeam = null;
const joinEl = document.getElementById('join');
const joinName = document.getElementById('join-name');
const joinGo = document.getElementById('join-go');

function refreshJoinGo() {
  joinGo.disabled = !(joinName.value.trim() && joinTeam);
  joinGo.textContent = profile ? 'Save' : 'Join the game';
}
function setJoinTeam(t) {
  joinTeam = t;
  document.getElementById('join-red').setAttribute('aria-pressed', String(t === 'red'));
  document.getElementById('join-blue').setAttribute('aria-pressed', String(t === 'blue'));
  refreshJoinGo();
}
function openJoin() {
  joinName.value = profile ? profile.name : '';
  setJoinTeam(profile ? profile.team : null);
  joinEl.classList.add('show');
}
document.getElementById('join-red').onclick = () => setJoinTeam('red');
document.getElementById('join-blue').onclick = () => setJoinTeam('blue');
joinName.addEventListener('input', refreshJoinGo);
joinName.addEventListener('keydown', e => { if (e.key === 'Enter' && !joinGo.disabled) joinGo.click(); });
joinGo.onclick = () => {
  profile = { name: joinName.value.trim(), team: joinTeam };
  try { localStorage.setItem('cc2-profile', JSON.stringify(profile)); } catch (e) {}
  you = profile.team;
  paintMe();
  joinEl.classList.remove('show');
  paint();
  if (current >= 0) showDetail(current);
};
document.getElementById('me').onclick = openJoin;

// Footer badge: fixed-size team-colored circle with the player's initial.
function paintMe() {
  const me = document.getElementById('me');
  const initial = (profile.name.trim()[0] || '?').toUpperCase();
  me.textContent = initial;
  me.className = profile.team === 'red' ? 'me-red' : 'me-blue';
  me.setAttribute('aria-label', `${profile.name}, Team ${TEAM_NAME[profile.team]} — change name or team`);
  me.title = `${profile.name} · Team ${TEAM_NAME[profile.team]}`;
}

/* ---------- start ---------- */
Promise.all([
  fetch('sf_neighborhoods.geojson').then(r => r.json()),
  fetch('challenges.json?v=' + Date.now()).then(r => r.json()).catch(err => { console.error('challenges.json', err); return {}; }),
]).then(async ([geo, chal]) => {
    CHALLENGES = CC.trios(chal);
    GEO = geo;
    buildMap(geo);
    buildTeams();
    rebuild();
    paint();
    // Is there a game server? (Not on the public site.) Without one, point to the replay site.
    let live = null;
    try {
      const r = await fetch('api/state?team=' + encodeURIComponent(you) + '&name=' + encodeURIComponent(profile ? profile.name : ''), { cache: 'no-store' });
      if (r.ok && (r.headers.get('Content-Type') || '').includes('json')) live = await r.json();
    } catch (e) {}
    if (!live) return noServer();
    S = live;
    await upLoad();
    if (S.phase === 'over') await startReplay();
    else { rebuild(); paint(); drawTeams(); }
    let saved = null; try { saved = localStorage.getItem('cc2-view'); } catch (e) {}
    setView(saved || 'map');
    if (profile) paintMe();
    else if (!OVER) openJoin();
    // A shared or refreshed #neighborhood URL opens that neighborhood directly.
    const target = decodeURIComponent(location.hash.slice(1));
    const ti = hoods.findIndex(h => h.name === target);
    if (ti >= 0) { navFromHistory = true; showDetail(ti); navFromHistory = false; }
    tick();
    flush();                       // late photos can still go up after the end
    if (!OVER) { poll(); startPings(); }
    else pollTimer = setTimeout(poll, 5000);
  });

// Opened without a game server (say, on the public site): say what this page is for.
function noServer() {
  document.querySelector('.join-card').innerHTML = `<h1>Clipper Conquest</h1>
    <p class="join-sub">This is the game app. It works while a game is running on the game server.</p>
    <a class="join-guide" href="https://mwhittaker.github.io/clipper_conquest/replay.html"><b>Watch a finished game</b><span>Open a replay file on the replay site</span></a>
    <a class="join-guide" href="https://mwhittaker.github.io/clipper_conquest/"><b>Read the guide</b><span>Rules, the rules video, the map and every challenge</span></a>`;
  document.getElementById('join').classList.add('show');
}
