#!/usr/bin/env python3
"""Compose every storyboard frame into one animated page (render/index.html) driven by
window.render(t), plus timeline.json with each beat's start/duration and voiceover offset.
Beat length = voiceover length + padding. Run video/frames/build.py first.
"""
import json, os, re, wave
HERE = os.path.dirname(os.path.abspath(__file__))
FR = os.path.join(HERE, '..', 'frames')
src = open(os.path.join(HERE, '..', 'storyboard.py')).read()
ns = {}; exec(src[src.index('BEATS = ['):src.index(']\nVOICES') + 1], ns)
BEATS = [b[0] for b in ns['BEATS']]

FPS, XFADE, LEAD, TAIL = 30, 0.45, 0.45, 0.75
def vo_len(b):
    p = os.path.join(HERE, 'vo', b + '.wav')
    if not os.path.exists(p): return 0.0
    w = wave.open(p); return w.getnframes() / w.getframerate()
MIN = {'0-tap': 3.6, '1a-draw': 3.6, '5b-blue': 3.4, '6b-sweep': 8.2, '7a-costs': 7.4, '8a-end': 7.5}
timeline, t = [], 0.0
for b in BEATS:
    v = vo_len(b)
    d = max(LEAD + v + TAIL, MIN.get(b, 2.5))
    if b == '2a-grey' and os.path.exists(os.path.join(HERE, 'vo', 'captions.json')):   # hold for the finale after the clock hits zero
        c2 = json.load(open(os.path.join(HERE, 'vo', 'captions.json')))['2a-grey']
        d = max(d, LEAD + c2[1][0] + .72 * (c2[1][1] - c2[1][0]) + 3.0)
    lead = {'4b-upload': 1.3}.get(b, LEAD)               # let the upload play out before "tap Complete"
    d = max(d, lead + v + TAIL)
    timeline.append({'id': b, 'start': round(t, 3), 'dur': round(d, 3), 'vo': round(t + lead, 3) if v else None})
    t += d
TOTAL = round(t + 0.6, 3)
CAPS = []
cp = os.path.join(HERE, 'vo', 'captions.json')
if os.path.exists(cp):
    cj = json.load(open(cp))
    for b in timeline:
        for s0, s1, txt in cj.get(b['id'], []):
            CAPS.append([round(b['vo'] + s0, 3), round(b['vo'] + s1, 3), txt])
def srt_t(x):
    h, r = divmod(x, 3600); m, r = divmod(r, 60); return f'{int(h):02}:{int(m):02}:{int(r):02},{int((r % 1) * 1000):03}'
with open(os.path.join(HERE, 'captions.srt'), 'w') as fh:
    for i, (a0, a1, txt) in enumerate(CAPS, 1):
        end = min(a1 + .35, CAPS[i][0] - .05) if i < len(CAPS) else a1 + .35
        fh.write(f'{i}\n{srt_t(a0)} --> {srt_t(end)}\n{txt}\n\n')

import sys; sys.path.insert(0, os.path.join(HERE, '..'))
from mapdata import HOODS
# title-card conquest: both teams leave FiDi and claim neighborhoods along a route
ROUTE = {'r': ['Financial District/South Beach', 'North Beach', 'Nob Hill', 'Tenderloin', 'South of Market', 'Mission',
               'Castro/Upper Market', 'Twin Peaks', 'Inner Sunset', 'Golden Gate Park', 'Haight Ashbury', 'Lone Mountain/USF', 'Pacific Heights'],
         'b': ['Financial District/South Beach', 'South of Market', 'Mission Bay', 'Potrero Hill', 'Bernal Heights', 'Mission',
               'Noe Valley', 'Castro/Upper Market', 'Hayes Valley', 'Western Addition', 'Japantown']}
# steals in order: red takes SoMa and the Mission from blue; blue takes the Mission back and steals the Castro
PTS = {n: [round(HOODS[n]['c'][0], 1), round(HOODS[n]['c'][1], 1)] for r in ROUTE.values() for n in r}
import layers
L_HTML, L_CSS, L_JS, EVENTS = layers.build(timeline, json.load(open(cp)) if os.path.exists(cp) else {})
css = head = None; sections = []
for i, b in enumerate(BEATS):
    h = open(os.path.join(FR, b + '.html')).read()
    if css is None:
        css = re.search(r'<style>(.*?)</style>', h, re.S).group(1)
        head = re.search(r'(<link[^>]+>)', h).group(1)
    body = re.search(r'<div class="stage">(.*)</div></body>', h, re.S).group(1)
    sections.append(f'<section class="beat" data-id="{b}" style="opacity:0">{body}</section>')

ANIM = r'''
const TL = __TL__, TOTAL = __TOTAL__, XF = __XF__, CAPS = __CAPS__, ROUTE = __ROUTE__, PTS = __PTS__;
const clamp = (x, a=0, b=1) => Math.max(a, Math.min(b, x));
const ease = x => { x = clamp(x); return 1 - Math.pow(1 - x, 3); };
const pop = x => { x = clamp(x); const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const beats = [...document.querySelectorAll('.beat')];
const byId = Object.fromEntries(beats.map(b => [b.dataset.id, b]));
// elements that enter with a staggered fade-up, per beat: [selector, first delay, gap]
const IN = {
  '1b-title': [['.side > *', .2, .35]],
  '2a-grey': [['.side > *', .4, .5]],
  '2b-challenges': [['.side .eyebrow, .side h2', .1, .15], ['.card', .8, 1.6], ['.side > div:last-child', 6.5, 0]],
  '3a-muni': [['.legend > *', 1.6, .9]],
  '4a-phone': [['.side > *', .3, .4]],
  '4b-upload': [['.side .eyebrow, .side h2', .1, .15], ['.side .row', 1.2, 1.1]],
  '5a-empty': [['.feed .row', .3, 0], ['.verdict', .8, 0]],
  '5b-blue': [['.feed > .row:nth-of-type(2)', .2, 0], ['.verdict', .7, 0]],
  '5c-tied1': [['.feed > .row:nth-of-type(3)', 4.6, 0], ['svg .badge', 4.6, 0], ['.verdict', 5.2, 0]],
  '5d-flip': [['.feed > .row:nth-of-type(4)', .2, 0], ['.feed .flip', 1.0, 0], ['.verdict', 1.6, 0]],
  '5e-tie2': [['.feed > .row:nth-of-type(5)', .2, 0], ['.verdict', 1.0, 0]],
  '6a-tiebreak': [['.side .eyebrow, .score', .1, .2], ['.tl .tt, .tl .dot', .8, .45], ['.tl .flag', 4.4, 0], ['.verdict', 5.0, 0]],
  '6b-sweep': [['.feed .row:not(.flip)', 1.2, 1.6], ['.feed .flip', 5.4, 0], ['.verdict', 6.0, 0]],
  '7a-costs': [['.legend > *', 1.0, .7]],
  '7b-stolen': [['.legend > *', .4, .6]],
  '8a-end': [['.side', .2, .6]],
};
const cache = {};
function parts(id) {
  if (cache[id]) return cache[id];
  const root = byId[id], out = [];
  for (const [sel, d0, gap] of (IN[id] || [])) root.querySelectorAll(sel).forEach((el, k) => out.push([el, d0 + k * gap]));
  const extra = {};
  if (id === '0-tap') extra.tap = { card: root.querySelector('#card'), reader: root.querySelector('#reader'), eraser: root.querySelector('#eraser'),
      idle: root.querySelector('#scr-idle'), ok: root.querySelector('#scr-ok'), check: root.querySelector('#okcheck'),
      rings: [...root.querySelectorAll('.ring')], sparks: [...root.querySelectorAll('.spark')] };
  if (id === '1b-title') { const svg = root.querySelector('.mapbox svg'), NS = 'http://www.w3.org/2000/svg';
    const paths = Object.fromEntries([...svg.querySelectorAll('path[data-n]')].map(p => [p.dataset.n, p]));
    const dots = {}; for (const [k, col] of [['b', '#1D6FB8'], ['r', '#C42847']]) { const c = document.createElementNS(NS, 'circle');
      c.setAttribute('r', 19); c.setAttribute('fill', col); c.setAttribute('stroke', '#fff'); c.setAttribute('stroke-width', 6); c.style.filter = 'drop-shadow(0 3px 4px rgba(28,30,33,.45))'; svg.appendChild(c); dots[k] = c; }
    extra.conquer = { paths, dots }; }
  if (id === '1a-draw') extra.draw = [...root.querySelectorAll('path')].map(p => { const L = p.getTotalLength(); p.style.strokeDasharray = L; return [p, L]; });
  if (id === '3a-muni') extra.routes = [...root.querySelectorAll('polyline')].map(p => { const L = p.getTotalLength(); p.style.strokeDasharray = L; return [p, L]; });
  if (id === '3a-muni') extra.dot = root.querySelector('circle');
  if (id === '6b-sweep') extra.lock = root.querySelector('.lockpop');
  if (id === '7a-costs' || id === '7b-stolen') extra.route = root.querySelector('polyline');
  if (id === '2a-grey') extra.count = root.querySelector('.big');
  if (id === '7a-costs') extra.badges = [...root.querySelectorAll('svg circle')].map(c => [c, c.nextElementSibling]);
  return cache[id] = { out, extra };
}
const easeIn = x => { x = clamp(x); return x * x * x; };
const inOut = x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
function tapScene(T, lt) {
  const r = ease(lt / .45);
  T.reader.style.opacity = r; T.reader.style.transform = `translateY(${(1 - r) * 40}px)`;
  // A hand-held feel: the card lands a little crooked and off-center, wobbles on the way in,
  // lifts off to the side so the screen shows, then flicks away. The scene then cross-dissolves.
  const CX = 960 + 16, CY = 350 + 10, TROT = -7, TAP = 1.2, HX = 1250, HY = 440;
  let x, y, rot, sc = 1;
  if (lt < TAP) { const p = inOut((lt - .3) / (TAP - .3)), s = Math.sin(p * Math.PI);
    x = CX + (1 - p) * 1150 + Math.sin(p * 9) * 18 * (1 - p); y = CY - s * 190 + (1 - p) * 140 + Math.sin(p * 13) * 8 * (1 - p);
    rot = (1 - p) * 55 + Math.sin(p * 7.5) * 14 * (1 - p) + TROT * p; sc = 1 + .08 * s; }
  else if (lt < 2.2) { const q = lt - TAP, h = inOut((q - .32) / .5);
    x = CX + (HX - CX) * h; y = CY + (HY - CY) * h + Math.sin(q * 3.2) * 5 * h; rot = TROT + (13 - TROT) * h + Math.sin(q * 2.6) * 2.5 * h;
    sc = 1 - .08 * Math.sin(Math.PI * clamp(q / .28)); }
  else { const q = easeIn((lt - 2.2) / .7); x = HX + q * 1100 + Math.sin(q * 5) * 30; y = HY - q * 420 + Math.sin(q * Math.PI) * 40; rot = 13 + q * 70; sc = 1 + q * .15; }
  T.card.style.transform = `translate(${x - 75}px, ${y - 120}px) rotate(${rot}deg) scale(${sc})`;
  T.eraser.style.display = 'none';
  const ok = clamp((lt - TAP - .05) / .12);
  T.idle.style.opacity = 1 - ok; T.ok.style.opacity = ok;
  if (!T.cl) { T.cl = T.check.getTotalLength(); T.check.style.strokeDasharray = T.cl; }
  T.check.style.strokeDashoffset = T.cl * (1 - ease((lt - TAP - .15) / .35));
  T.rings.forEach((g, i) => { const p = clamp((lt - TAP - i * .14) / .9); const R = 50 + 320 * ease(p);
    g.style.width = g.style.height = 2 * R + 'px'; g.style.marginLeft = g.style.marginTop = -R + 'px';
    g.style.opacity = p > 0 && p < 1 ? (1 - p) * .8 : 0; g.style.borderWidth = (8 - 5 * p) + 'px'; });
  T.sparks.forEach((g, i) => { const a = i * 2.39996 + .3, D = 190 + (i * 53) % 220;
    const p = clamp((lt - TAP - .02 - (i % 5) * .03) / 1.0), e = ease(p);
    g.style.transform = `translate(${Math.cos(a) * D * e}px, ${Math.sin(a) * D * e + 60 * p * p}px) rotate(${e * 200 + i * 20}deg) scale(${p > 0 ? 1.1 - .7 * p : 0})`;
    g.style.opacity = p > 0 && p < 1 ? 1 - p * p : 0; });
}
function conquerScene(C, lt, dur) {
  // each team's dot hops centroid to centroid; a neighborhood shows whichever team reached it most recently
  const T0 = .5, T1 = dur - .4, COL = { r: '#C42847', b: '#1D6FB8' }, last = {};
  for (const team of ['r', 'b']) {
    const R = ROUTE[team], n = R.length - 1, per = (T1 - T0) / n, u = (lt - T0) / per;
    const i = Math.max(0, Math.min(n - 1, Math.floor(u))), f = inOut(clamp(u - i));
    const a = PTS[R[i]], b = PTS[R[i + 1]], hop = Math.sin(Math.PI * clamp(u - i)) * 12;
    const x = u <= 0 ? PTS[R[0]][0] : a[0] + (b[0] - a[0]) * f, y = u <= 0 ? PTS[R[0]][1] : a[1] + (b[1] - a[1]) * f - hop;
    C.dots[team].setAttribute('cx', x); C.dots[team].setAttribute('cy', y);
    C.dots[team].style.opacity = ease(lt / .3);
    R.forEach((name, k) => { if (team === 'r' && k === 0) return;   // blue reaches FiDi first
      const at = T0 + k * per; if (lt >= at - .02 && (!last[name] || at > last[name].at)) last[name] = { team, at }; });
  }
  for (const [name, p] of Object.entries(C.paths)) {
    const L = last[name];
    if (!L) { p.style.fill = '#F1F2EE'; p.style.filter = ''; continue; }
    p.style.fill = COL[L.team];
    const age = lt - L.at; p.style.filter = age < .3 ? `brightness(${1.45 - 1.5 * age})` : '';
  }
}
window.render = function (t) {
  let cur = 0;
  TL.forEach((b, i) => { if (t >= b.start) cur = i; });
  beats.forEach(el => { el.style.opacity = 0; el.style.zIndex = 0; });
  const show = (i, op) => {
    const b = TL[i], el = byId[b.id], lt = t - b.start;
    el.style.opacity = op; el.style.zIndex = 1 + i;
    el.style.transform = `scale(${1.015 - .015 * ease(lt / .8)})`;
    const { out, extra } = parts(b.id);
    for (const [e, d] of out) { const p = ease((lt - d) / .45); e.style.opacity = p; e.style.transform = `translateY(${(1 - p) * 22}px)`; }
    if (extra.tap) tapScene(extra.tap, lt);
    if (extra.conquer) conquerScene(extra.conquer, lt, b.dur);
    if (extra.draw) extra.draw.forEach(([p, L], k) => { p.style.strokeDashoffset = L * (1 - ease((lt - .15 - k * .045) / .7)); });
    if (extra.routes) extra.routes.forEach(([p, L], k) => { p.style.strokeDashoffset = L * (1 - ease((lt - .2 - k * .06) / 1.1)); });
    if (extra.dot) { const p = ease((lt - 1.4) / .4); extra.dot.style.opacity = p; extra.dot.setAttribute('r', 20 * pop((lt - 1.4) / .5)); }
    if (extra.lock) { const p = clamp((lt - 5.4) / .45); extra.lock.style.opacity = p > 0 ? 1 : 0; extra.lock.style.transform = `scale(${p > 0 ? pop(p) : 0})`; }
    if (extra.route) { extra.route.style.opacity = ease((lt - (b.id === '7a-costs' ? 3.4 : .2)) / .6); }
    if (extra.count) extra.count.textContent = Math.round(41 * ease((lt - .3) / 1.6));
    if (extra.badges) extra.badges.forEach(([c, g], k) => { const o = ease((lt - .3 - k * .05) / .3); c.style.opacity = o; if (g && g.tagName !== 'circle') g.style.opacity = o; });
  };
  const b = TL[cur], lt = t - b.start;
  const xf = TL[cur].id === '1b-title' ? .8 : XF;
  if (cur > 0 && lt < xf) { show(cur - 1, 1); show(cur, ease(lt / xf)); }
  else show(cur, 1);
  if (t > TOTAL - .6) byId[TL[TL.length - 1].id].style.opacity = clamp((TOTAL - t) / .6);
  const cap = document.getElementById('cap'); let txt = '';
  CAPS.forEach(([a, b, s], i) => { const end = i + 1 < CAPS.length ? Math.min(b + .35, CAPS[i + 1][0] - .05) : b + .35; if (t >= a - .05 && t < end) txt = s; });
  cap.textContent = txt; cap.style.opacity = txt ? 1 : 0;
  renderLayers(t);
};
'''.replace('__TL__', json.dumps(timeline)).replace('__TOTAL__', str(TOTAL)).replace('__XF__', str(XFADE)).replace('__CAPS__', json.dumps(CAPS)).replace('__ROUTE__', json.dumps(ROUTE)).replace('__PTS__', json.dumps(PTS))

page = f'''<!doctype html><html><head><meta charset="utf-8">{head}<style>{css}
.beat {{ position:absolute; inset:0; background:#fff; transform-origin:50% 50%; }}
#cap {{ position:absolute; left:50%; bottom:40px; transform:translateX(-50%); z-index:100; max-width:1500px; width:max-content;
  background:rgba(28,30,33,.86); color:#fff; font:600 38px/1.3 Inter, system-ui, sans-serif; padding:12px 30px; border-radius:16px;
  text-align:center; text-wrap:balance; }}
{L_CSS}
</style></head><body><div class="stage"><svg width="0" height="0" style="position:absolute"><defs><pattern id="tie" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="14" height="28" fill="#C42847"/><rect x="14" width="14" height="28" fill="#1D6FB8"/></pattern></defs></svg>{"".join(sections)}{L_HTML}<div id="cap"></div></div>
<script>{ANIM}\n{L_JS}</script></body></html>'''
open(os.path.join(HERE, 'index.html'), 'w').write(page)
json.dump({'fps': FPS, 'total': TOTAL, 'beats': timeline, 'events': EVENTS}, open(os.path.join(HERE, 'timeline.json'), 'w'), indent=1)
print(f'index.html: {len(page)//1024} KB, {len(BEATS)} beats, total {TOTAL:.1f}s = {int(TOTAL*FPS)} frames')
