#!/usr/bin/env python3
"""Compose every scene frame into one animated page, index.html, driven by
window.render(t). Also writes timeline.json (each beat's start, duration and voiceover
offset, plus sound-effect times for mix.py), captions.srt, and vo/lines.json (the
voiceover lines from beats.py, for kokoro/tts.py). A beat lasts its voiceover plus
padding. Run video/frames/build.py first.
"""
import json, os, re, sys, wave
HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES_DIR = os.path.join(HERE, '..', 'frames')
VO_DIR = os.path.join(HERE, 'vo')
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
import layers
from beats import BEATS

BEAT_IDS = [b[0] for b in BEATS]
with open(os.path.join(VO_DIR, 'lines.json'), 'w') as fh:
    json.dump([{'id': b[0], 'text': b[3]} for b in BEATS if b[3]], fh, indent=1)

# Kokoro's per-sentence timings {beat id: [[start, end, sentence], ...]}, relative to each clip
CAPTIONS_JSON = os.path.join(VO_DIR, 'captions.json')
VO_CAPTIONS = json.load(open(CAPTIONS_JSON)) if os.path.exists(CAPTIONS_JSON) else {}

# ---------- timing ----------
FPS = 30
XFADE = 0.45        # cross-fade between beats (s)
LEAD = 0.45         # from the start of a beat to its voiceover
TAIL = 0.75         # after the voiceover ends
MIN_DUR = {'0-tap': 3.6, '5b-blue': 3.4, '6b-sweep': 8.2, '7a-costs': 7.4, '8a-end': 7.5}   # default 2.5
VO_LEAD = {'4b-upload': 1.3}   # let the upload play out before "tap Complete"


def vo_len(beat_id):
    """Length in seconds of a beat's voiceover clip (0 if it has none)."""
    p = os.path.join(VO_DIR, beat_id + '.wav')
    if not os.path.exists(p): return 0.0
    with wave.open(p) as w:
        return w.getnframes() / w.getframerate()


timeline, t = [], 0.0
for b in BEAT_IDS:
    v = vo_len(b)
    lead = VO_LEAD.get(b, LEAD)
    d = max(lead + v + TAIL, MIN_DUR.get(b, 2.5))
    if b == '2a-grey' and VO_CAPTIONS:   # hold for the finale after the clock hits zero
        d = max(d, LEAD + layers.zero_offset(VO_CAPTIONS['2a-grey']) + 3.0)
    timeline.append({'id': b, 'start': round(t, 3), 'dur': round(d, 3), 'vo': round(t + lead, 3) if v else None})
    t += d
TOTAL = round(t + 0.6, 3)   # the last beat fades out over its final 0.6 s

# ---------- captions ----------
CAPS = [[round(b['vo'] + s0, 3), round(b['vo'] + s1, 3), txt]
        for b in timeline for s0, s1, txt in VO_CAPTIONS.get(b['id'], [])]


def caption_end(i):
    """Caption i stays up 0.35 s past its sentence, but clears 0.05 s before the next one."""
    end = CAPS[i][1] + .35
    return min(end, CAPS[i + 1][0] - .05) if i + 1 < len(CAPS) else end


def srt_time(x):
    h, r = divmod(x, 3600); m, r = divmod(r, 60)
    return f'{int(h):02}:{int(m):02}:{int(r):02},{int((r % 1) * 1000):03}'


with open(os.path.join(HERE, 'captions.srt'), 'w') as fh:
    for i, (start, _, txt) in enumerate(CAPS):
        fh.write(f'{i + 1}\n{srt_time(start)} --> {srt_time(caption_end(i))}\n{txt}\n\n')

# ---------- the page ----------
L_HTML, L_CSS, L_JS, EVENTS = layers.build(timeline, VO_CAPTIONS)
# every scene shares the same <style> and font <link>, so take them from the first
css = head = None; sections = []
for b in BEAT_IDS:
    h = open(os.path.join(FRAMES_DIR, b + '.html')).read()
    if css is None:
        css = re.search(r'<style>(.*?)</style>', h, re.S).group(1)
        head = re.search(r'(<link[^>]+>)', h).group(1)
    body = re.search(r'<div class="stage">(.*)</div></body>', h, re.S).group(1)
    sections.append(f'<section class="beat" data-id="{b}" style="opacity:0">{body}</section>')

# window.render(t): cross-fades the beats, animates each beat's own elements, shows the
# captions, then calls renderLayers(t) from layers.py.
ANIM = r'''
const TL = __TL__, TOTAL = __TOTAL__, XF = __XF__, CAPS = __CAPS__, LOCK_AT = __LOCK__;
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
  '6b-sweep': [['.feed .row:not(.flip)', 1.2, 1.6], ['.feed .flip', LOCK_AT, 0], ['.verdict', LOCK_AT + .6, 0]],
  '7a-costs': [['.legend > *', 1.0, .7]],
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
  if (id === '3a-muni') extra.routes = [...root.querySelectorAll('polyline')].map(p => { const L = p.getTotalLength(); p.style.strokeDasharray = L; return [p, L]; });
  if (id === '3a-muni') extra.dot = root.querySelector('circle');
  if (id === '6b-sweep') extra.lock = root.querySelector('.lockpop');
  if (id === '7a-costs') extra.route = root.querySelector('polyline');
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
    if (extra.routes) extra.routes.forEach(([p, L], k) => { p.style.strokeDashoffset = L * (1 - ease((lt - .2 - k * .06) / 1.1)); });
    if (extra.dot) { const p = ease((lt - 1.4) / .4); extra.dot.style.opacity = p; extra.dot.setAttribute('r', 20 * pop((lt - 1.4) / .5)); }
    if (extra.lock) { const p = clamp((lt - LOCK_AT) / .45); extra.lock.style.opacity = p > 0 ? 1 : 0; extra.lock.style.transform = `scale(${p > 0 ? pop(p) : 0})`; }
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
'''

for key, value in {'__TL__': json.dumps(timeline), '__TOTAL__': str(TOTAL), '__XF__': str(XFADE),
                   '__CAPS__': json.dumps(CAPS), '__LOCK__': str(layers.LOCK_AT)}.items():
    ANIM = ANIM.replace(key, value)

page = f'''<!doctype html><html><head><meta charset="utf-8">{head}<style>{css}
.beat {{ position:absolute; inset:0; background:#fff; transform-origin:50% 50%; }}
#cap {{ position:absolute; left:50%; bottom:40px; transform:translateX(-50%); z-index:100; max-width:1500px; width:max-content;
  background:rgba(28,30,33,.86); color:#fff; font:600 38px/1.3 Inter, system-ui, sans-serif; padding:12px 30px; border-radius:16px;
  text-align:center; text-wrap:balance; }}
{L_CSS}
</style></head><body><div class="stage"><svg width="0" height="0" style="position:absolute"><defs><pattern id="tie" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="14" height="28" fill="#C42847"/><rect x="14" width="14" height="28" fill="#1D6FB8"/></pattern></defs></svg>{"".join(sections)}{L_HTML}<div id="cap"></div></div>
<script>{ANIM}\n{L_JS}</script></body></html>'''
with open(os.path.join(HERE, 'index.html'), 'w') as fh:
    fh.write(page)
with open(os.path.join(HERE, 'timeline.json'), 'w') as fh:
    json.dump({'fps': FPS, 'total': TOTAL, 'beats': timeline, 'events': EVENTS}, fh, indent=1)
print(f'index.html: {len(page)//1024} KB, {len(BEAT_IDS)} beats, total {TOTAL:.1f}s = {int(TOTAL*FPS)} frames')
