// Shared map geometry + game scenario for the Clipper Conquest design mockups.
// Every mockup renders this same game moment so the five designs are comparable.
//
// Usage from a mockup page:
//   <script src="shared.js"></script>
//   const svg = document.querySelector('svg.cc-map');   // give it viewBox="0 0 200 200"
//   ccRenderMap(svg, { badges: true, labels: ['mission','sunset'] });
//
// ccRenderMap adds, per neighborhood, a <polygon class="hood hood--STATE" data-id="...">
// where STATE is one of: fog | surf | tied | open, plus class "hood--selected" on the
// selected neighborhood (Mission). Parks get <polygon class="park">. If opts.badges,
// neighborhoods where anything has happened also get a <text class="hood-badge"> at the
// centroid reading e.g. "2–1" (fog count first). If opts.labels lists ids, those get a
// <text class="hood-label"> with the display name. All styling is left to your CSS.
// You may also ignore ccRenderMap and draw your own map from CC.HOODS / CC.PARKS.

const CC = {
  teams: {
    fog:  { name: 'Team Fog',  short: 'FOG' },
    surf: { name: 'Team Surf', short: 'SURF' },
  },
  // Live score = neighborhoods currently held. Fog holds 4, Surf holds 3,
  // 2 are tied ("contested"), 6 untouched. Challenge totals: Fog 11, Surf 10.
  score: { fog: 4, surf: 3, contested: 2, open: 6 },
  clock: '2:47:12',          // time remaining
  you: 'fog',                // the viewer plays on Team Fog
  selected: 'mission',       // neighborhood whose detail sheet is open

  // Stylized SF, viewBox 0 0 200 200. North up. Not geographically exact on purpose.
  HOODS: [
    { id: 'richmond',   name: 'Richmond',      pts: [[8,50],[76,52],[76,76],[8,74]] },
    { id: 'marina',     name: 'Marina',        pts: [[76,24],[110,16],[112,44],[76,48]] },
    { id: 'northbeach', name: 'North Beach',   pts: [[110,16],[146,10],[158,38],[112,44]] },
    { id: 'westadd',    name: 'Western Addition', pts: [[76,52],[136,50],[136,78],[88,78],[76,76]] },
    { id: 'fidi',       name: 'Downtown',      pts: [[112,44],[158,38],[184,56],[180,80],[136,78],[136,50]] },
    { id: 'sunset',     name: 'Sunset',        pts: [[8,96],[76,96],[74,150],[10,148]] },
    { id: 'haight',     name: 'Haight',        pts: [[88,80],[130,80],[130,106],[88,94]] },
    { id: 'soma',       name: 'SoMa',          pts: [[130,80],[180,80],[172,112],[130,108]] },
    { id: 'castro',     name: 'Castro',        pts: [[76,98],[88,94],[130,106],[128,132],[78,134]] },
    { id: 'mission',    name: 'Mission',       pts: [[130,108],[172,112],[168,150],[130,148]] },
    { id: 'potrero',    name: 'Potrero Hill',  pts: [[172,112],[192,110],[194,148],[168,150]] },
    { id: 'noe',        name: 'Noe Valley',    pts: [[78,134],[128,132],[126,156],[80,158]] },
    { id: 'merced',     name: 'Lake Merced',   pts: [[10,148],[74,150],[76,184],[14,180]] },
    { id: 'excelsior',  name: 'Excelsior',     pts: [[80,158],[126,156],[130,148],[148,158],[150,186],[84,184]] },
    { id: 'bayview',    name: 'Bayview',       pts: [[150,158],[192,150],[188,190],[152,188]] },
  ],
  PARKS: [
    { id: 'presidio', name: 'Presidio',         pts: [[8,26],[50,18],[76,24],[76,48],[36,50],[10,46]] },
    { id: 'ggpark',   name: 'Golden Gate Park', pts: [[8,78],[88,78],[88,94],[8,92]] },
  ],

  // Challenge completions per neighborhood: [fog, surf] out of 3.
  state: {
    richmond:   [2, 0], marina: [3, 0], northbeach: [2, 1], haight: [1, 0],
    mission:    [1, 2], soma:   [0, 2], castro:     [0, 3],
    sunset:     [1, 1], fidi:   [1, 1],
    westadd: [0, 0], potrero: [0, 0], noe: [0, 0],
    merced:  [0, 0], excelsior: [0, 0], bayview: [0, 0],
  },

  // The open detail sheet: Mission, Surf leads 2-1. Fog can flip it by
  // completing its two remaining challenges (each team completes challenges
  // independently; a Surf completion never blocks a Fog one).
  detail: {
    id: 'mission',
    challenges: [
      { n: 1, title: 'Order in Spanish at a taqueria',        fog: false, surf: '2:14 PM' },
      { n: 2, title: 'Find the oldest mural on Balmy Alley',  fog: '1:52 PM', surf: '2:31 PM' },
      { n: 3, title: 'Team photo on top of Dolores Park hill', fog: false, surf: false },
    ],
    note: 'Surf holds Mission 2–1. Complete 2 more to flip it.',
  },

  // Recent activity, newest first (for feeds / tickers).
  feed: [
    { t: '2:31 PM', team: 'surf', text: 'Surf completed “Find the oldest mural on Balmy Alley” in Mission' },
    { t: '2:14 PM', team: 'surf', text: 'Surf completed “Order in Spanish at a taqueria” — Surf takes Mission 2–1' },
    { t: '1:58 PM', team: 'fog',  text: 'Fog completed challenge 3 in Marina — Marina locked at 3' },
    { t: '1:52 PM', team: 'fog',  text: 'Fog completed “Find the oldest mural on Balmy Alley” in Mission' },
    { t: '1:37 PM', team: 'surf', text: 'Surf completed challenge 2 in Castro — Castro swept 0–3' },
  ],
};

function ccHoodState(id) {
  const [f, s] = CC.state[id] || [0, 0];
  if (f === 0 && s === 0) return 'open';
  if (f === s) return 'tied';
  return f > s ? 'fog' : 'surf';
}

function ccCentroid(pts) {
  const x = pts.reduce((a, p) => a + p[0], 0) / pts.length;
  const y = pts.reduce((a, p) => a + p[1], 0) / pts.length;
  return [x, y];
}

function ccRenderMap(svg, opts = {}) {
  const NS = 'http://www.w3.org/2000/svg';
  const poly = (pts, cls, id) => {
    const el = document.createElementNS(NS, 'polygon');
    el.setAttribute('points', pts.map(p => p.join(',')).join(' '));
    el.setAttribute('class', cls);
    if (id) el.dataset.id = id;
    svg.appendChild(el);
    return el;
  };
  const text = (x, y, str, cls) => {
    const el = document.createElementNS(NS, 'text');
    el.setAttribute('x', x); el.setAttribute('y', y);
    el.setAttribute('class', cls);
    el.setAttribute('text-anchor', 'middle');
    el.textContent = str;
    svg.appendChild(el);
    return el;
  };
  CC.PARKS.forEach(p => poly(p.pts, 'park', p.id));
  CC.HOODS.forEach(h => {
    let cls = `hood hood--${ccHoodState(h.id)}`;
    if (h.id === CC.selected) cls += ' hood--selected';
    poly(h.pts, cls, h.id);
  });
  if (opts.badges) {
    CC.HOODS.forEach(h => {
      const [f, s] = CC.state[h.id];
      if (f || s) {
        const [x, y] = ccCentroid(h.pts);
        text(x, y + 2, `${f}–${s}`, `hood-badge hood-badge--${ccHoodState(h.id)}`);
      }
    });
  }
  (opts.labels || []).forEach(id => {
    const h = CC.HOODS.find(n => n.id === id) || CC.PARKS.find(n => n.id === id);
    if (!h) return;
    const [x, y] = ccCentroid(h.pts);
    text(x, y - (CC.state[h.id] && (CC.state[h.id][0] || CC.state[h.id][1]) ? 4 : -1),
         h.name, 'hood-label');
  });
}
