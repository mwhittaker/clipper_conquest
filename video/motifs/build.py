#!/usr/bin/env python3
"""Render three candidate visual motifs for the rules video as 1920x1080 HTML frames:
a title card and a mid-game tiebreak frame for each. Screenshot them with headless
Chrome (see README in this folder). Output: video/motifs/{a,b,c}-{title,tie}.html
"""
import json, math, os, html
HERE = os.path.dirname(os.path.abspath(__file__))
geo = json.load(open(os.path.join(HERE, '../../mockups/sf_neighborhoods.geojson')))

# ---------- projection into a 1000 x H box ----------
def rings(g):
    return [p[0] for p in g['coordinates']] if g['type'] == 'MultiPolygon' else [g['coordinates'][0]]
pts = [c for f in geo['features'] for r in rings(f['geometry']) for c in r]
lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
kx = math.cos(math.radians((lat0 + lat1) / 2))
S = 1000 / ((lon1 - lon0) * kx)
H = (lat1 - lat0) * S
def P(c): return ((c[0] - lon0) * kx * S, (lat1 - c[1]) * S)

def area(r): return 0.5 * sum(r[i-1][0]*r[i][1] - r[i][0]*r[i-1][1] for i in range(len(r)))
def inside(r, x, y):
    c = False
    for i in range(len(r)):
        (x1, y1), (x2, y2) = r[i-1], r[i]
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c = not c
    return c
def segd(px, py, a, b):
    (x1, y1), (x2, y2) = a, b; dx, dy = x2-x1, y2-y1
    t = max(0, min(1, ((px-x1)*dx+(py-y1)*dy)/((dx*dx+dy*dy) or 1)))
    return math.hypot(px-x1-t*dx, py-y1-t*dy)
def pole(r):
    xs, ys = [p[0] for p in r], [p[1] for p in r]
    best, bp = -1, (sum(xs)/len(xs), sum(ys)/len(ys))
    for i in range(40):
        for j in range(40):
            x = min(xs) + (max(xs)-min(xs))*(i+.5)/40; y = min(ys) + (max(ys)-min(ys))*(j+.5)/40
            if inside(r, x, y):
                d = min(segd(x, y, r[k-1], r[k]) for k in range(len(r)))
                if d > best: best, bp = d, (x, y)
    return bp

HOODS = {}
for f in geo['features']:
    rs = [[P(c) for c in r] for r in rings(f['geometry'])]
    d = ' '.join('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in r) + 'Z' for r in rs)
    big = max(rs, key=lambda r: abs(area(r)))
    HOODS[f['properties']['name']] = {'d': d, 'c': pole(big)}

# ---------- mid-game scenario (red, blue); holder decided by count, ties noted ----------
SCORE = {
 'Mission': (2, 2, 'r'), 'Hayes Valley': (0, 3, 'b'), 'Western Addition': (0, 1, 'b'),
 'Haight Ashbury': (1, 0, 'r'), 'Castro/Upper Market': (2, 0, 'r'), 'Noe Valley': (1, 2, 'b'),
 'Bernal Heights': (3, 0, 'r'), 'Potrero Hill': (2, 1, 'r'), 'South of Market': (1, 2, 'b'),
 'Financial District/South Beach': (0, 2, 'b'), 'Chinatown': (0, 1, 'b'), 'North Beach': (1, 1, 'b'),
 'Nob Hill': (2, 0, 'r'), 'Tenderloin': (1, 0, 'r'), 'Russian Hill': (0, 2, 'b'),
 'Marina': (0, 1, 'b'), 'Pacific Heights': (1, 0, 'r'), 'Mission Bay': (0, 3, 'b'),
 'Inner Sunset': (2, 0, 'r'), 'Golden Gate Park': (1, 0, 'r'), 'Twin Peaks': (1, 0, 'r'),
 'Glen Park': (2, 1, 'r'), 'Japantown': (0, 2, 'b'), 'Lone Mountain/USF': (1, 0, 'r'),
}
red = sum(1 for v in SCORE.values() if v[2] == 'r'); blue = sum(1 for v in SCORE.values() if v[2] == 'b')

def svg_map(theme, focus=None, scores=True, labels=False):
    parts = []
    for n, h in HOODS.items():
        cls = 'n'
        if n in SCORE: cls = 'r' if SCORE[n][2] == 'r' else 'b'
        if scores is False: cls = 'n'
        if n == focus: cls += ' focus'
        parts.append(f'<path class="{cls}" d="{h["d"]}"><title>{html.escape(n)}</title></path>')
    if scores is True:
        for n, (r, b, _) in SCORE.items():
            x, y = HOODS[n]['c']
            locked = ' lock' if 3 in (r, b) else ''
            parts.append(f'<g class="sc{locked}" transform="translate({x:.0f},{y:.0f})">'
                         f'<text class="sr" x="-4" text-anchor="end">{r}</text>'
                         f'<text class="sd">·</text>'
                         f'<text class="sb" x="4">{b}</text></g>')
    return f'<svg class="map {theme}" viewBox="-10 -10 1020 {H+20:.0f}" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'

TIMELINE = [('b', '11:04', 1), ('r', '11:40', 1), ('r', '11:58', 2), ('b', '12:30', 2)]
def timeline():
    t0, t1 = 11*60, 13*60
    def x(t): h, m = map(int, t.split(':')); return 6 + 88*((h*60+m)-t0)/(t1-t0)
    dots = ''.join(f'<div class="td {c}" style="left:{x(t):.1f}%"><span class="tt">{t}</span><span class="tn">{n}</span></div>'
                   for c, t, n in TIMELINE)
    return f'<div class="tl"><div class="track"></div>{dots}<div class="flag" style="left:{x("11:58"):.1f}%">Red reaches 2 first</div></div>'

FONTS = {
 'a': 'family=Archivo:wght@500;700;800;900&family=Archivo+Narrow:wght@500;700',
 'b': 'family=Rubik:wght@500;700;800;900&family=Rubik+Mono+One',
 'c': 'family=Saira+Condensed:wght@500;700;800;900&family=Saira:wght@400;600',
}

CSS = {
# ---------------- A: Muni signage — flat, white, route bullets, thick rules ----------------
'a': """
body { background:#F4F5F2; color:#111; font-family:'Archivo',sans-serif; }
.map .n { fill:#DADDD8; stroke:#F4F5F2; stroke-width:2.5; }
.map .r { fill:#C42847; stroke:#F4F5F2; stroke-width:2.5; }
.map .b { fill:#1D6FB8; stroke:#F4F5F2; stroke-width:2.5; }
.map .focus { stroke:#111; stroke-width:6; }
.sc text { font:800 24px 'Archivo Narrow',sans-serif; fill:#fff; dominant-baseline:middle; }
.sc .sd { text-anchor:middle; }
.sc.lock text { fill:#fff; }
.bar { position:absolute; left:0; right:0; top:0; height:14px; background:#111; }
.title .kicker { font:700 30px 'Archivo Narrow'; letter-spacing:.2em; text-transform:uppercase; }
.title h1 { font-weight:900; font-size:150px; line-height:.86; letter-spacing:-.02em; margin:24px 0; }
.title h1 .c { color:#1D6FB8; } .title h1 .q { color:#C42847; }
.title .tag { font:700 44px 'Archivo'; }
.title .bullets { display:flex; gap:18px; margin-top:60px; }
.bullet { width:92px; height:92px; border-radius:50%; display:grid; place-items:center; color:#fff; font:900 46px 'Archivo'; }
.hud { font-family:'Archivo Narrow'; }
.clock { background:#111; color:#fff; padding:14px 26px; font:800 64px 'Archivo'; font-variant-numeric:tabular-nums; letter-spacing:.02em; }
.tally { display:flex; gap:14px; }
.tally div { color:#fff; padding:12px 24px; font:800 40px 'Archivo'; }
.tally .r { background:#C42847; } .tally .b { background:#1D6FB8; }
.panel { background:#fff; border-top:14px solid #111; padding:40px 44px; }
.panel .eyebrow { font:700 26px 'Archivo Narrow'; letter-spacing:.18em; text-transform:uppercase; color:#555; }
.panel h2 { font:900 84px 'Archivo'; margin:6px 0 20px; letter-spacing:-.01em; }
.panel .score { font:900 120px 'Archivo'; line-height:1; }
.panel .score .r { color:#C42847; } .panel .score .b { color:#1D6FB8; } .panel .score .x { color:#bbb; }
.tl .track { background:#111; height:6px; }
.td { width:34px; height:34px; border-radius:50%; border:5px solid #fff; }
.td.r { background:#C42847; } .td.b { background:#1D6FB8; }
.tt { font:700 24px 'Archivo Narrow'; color:#333; } .tn { font:900 22px 'Archivo'; color:#fff; }
.flag { background:#111; color:#fff; font:800 26px 'Archivo'; padding:8px 14px; }
.verdict { font:800 40px 'Archivo'; } .verdict b { color:#C42847; }
""",
# ---------------- B: board game — tilted tabletop, raised tiles, tokens ----------------
'b': """
body { background: radial-gradient(ellipse at 50% 40%, #3E4C5A 0%, #1F2730 75%); color:#F3EEE4; font-family:'Rubik',sans-serif; }
.table { filter: drop-shadow(0 40px 40px rgba(0,0,0,.45)); }
.map .n { fill:#CFC8BA; stroke:#8C8475; stroke-width:2; filter:url(#tile); }
.map .r { fill:#D8455E; stroke:#7E1C2E; stroke-width:2; filter:url(#tile); }
.map .b { fill:#3C86C9; stroke:#153F66; stroke-width:2; filter:url(#tile); }
.map .focus { stroke:#FFD447; stroke-width:7; }
.sc text { font:900 26px 'Rubik'; fill:#fff; dominant-baseline:middle; paint-order:stroke; stroke:rgba(0,0,0,.45); stroke-width:5px; }
.sc .sd { text-anchor:middle; }
.title .kicker { font:700 30px 'Rubik'; letter-spacing:.14em; text-transform:uppercase; color:#FFD447; }
.title h1 { font:400 112px 'Rubik Mono One'; line-height:.92; margin:26px 0; }
.title h1 .c { color:#6FB2EE; } .title h1 .q { color:#F26B82; }
.title .tag { font:700 46px 'Rubik'; }
.title .bullets { display:flex; gap:26px; margin-top:56px; }
.bullet { width:88px; height:88px; border-radius:50%; display:grid; place-items:center; font:900 40px 'Rubik'; color:#fff;
  box-shadow: inset 0 -8px 0 rgba(0,0,0,.25), 0 10px 18px rgba(0,0,0,.4); }
.clock { background:#F3EEE4; color:#1F2730; padding:12px 26px; border-radius:18px; font:900 60px 'Rubik'; font-variant-numeric:tabular-nums;
  box-shadow: 0 8px 0 #B9AE98, 0 16px 30px rgba(0,0,0,.4); }
.tally { display:flex; gap:16px; }
.tally div { color:#fff; padding:12px 26px; border-radius:16px; font:900 40px 'Rubik'; box-shadow: 0 7px 0 rgba(0,0,0,.3); }
.tally .r { background:#D8455E; } .tally .b { background:#3C86C9; }
.panel { background:#F3EEE4; color:#1F2730; border-radius:28px; padding:40px 44px; box-shadow: 0 12px 0 #B9AE98, 0 30px 60px rgba(0,0,0,.45); transform: rotate(1.2deg); }
.panel .eyebrow { font:700 26px 'Rubik'; letter-spacing:.14em; text-transform:uppercase; color:#8C8475; }
.panel h2 { font:900 80px 'Rubik'; margin:6px 0 20px; }
.panel .score { font:400 110px 'Rubik Mono One'; line-height:1; }
.panel .score .r { color:#D8455E; } .panel .score .b { color:#3C86C9; } .panel .score .x { color:#C7BFAF; }
.tl .track { background:#C7BFAF; height:10px; border-radius:5px; }
.td { width:44px; height:44px; border-radius:50%; box-shadow: inset 0 -6px 0 rgba(0,0,0,.25), 0 6px 10px rgba(0,0,0,.3); }
.td.r { background:#D8455E; } .td.b { background:#3C86C9; }
.tt { font:700 24px 'Rubik'; color:#5E574B; } .tn { font:900 22px 'Rubik'; color:#fff; }
.flag { background:#FFD447; color:#1F2730; font:900 26px 'Rubik'; padding:8px 16px; border-radius:12px; }
.verdict { font:800 40px 'Rubik'; } .verdict b { color:#D8455E; }
""",
# ---------------- C: night broadcast — dark, glowing edges, fog, sports scorebug ----------------
'c': """
body { background:#070B14; color:#EAF0FA; font-family:'Saira',sans-serif; }
.fog { position:absolute; inset:0; background:
   radial-gradient(ellipse 60% 40% at 20% 30%, rgba(160,180,210,.10), transparent 70%),
   radial-gradient(ellipse 50% 35% at 75% 70%, rgba(160,180,210,.08), transparent 70%); pointer-events:none; }
.map .n { fill:#0F1726; stroke:#34435E; stroke-width:1.8; }
.map .r { fill:rgba(255,64,99,.28); stroke:#FF4063; stroke-width:2.6; filter:url(#glow); }
.map .b { fill:rgba(56,156,255,.26); stroke:#389CFF; stroke-width:2.6; filter:url(#glow); }
.map .focus { stroke:#fff; stroke-width:5; }
.sc text { font:800 26px 'Saira Condensed'; dominant-baseline:middle; }
.sc .sr { fill:#FF7A93; } .sc .sb { fill:#7CC0FF; } .sc .sd { fill:#8894AA; text-anchor:middle; }
.title .kicker { font:600 30px 'Saira'; letter-spacing:.32em; text-transform:uppercase; color:#8894AA; }
.title h1 { font:900 190px 'Saira Condensed'; line-height:.82; margin:26px 0; letter-spacing:.01em; }
.title h1 .c { color:#389CFF; text-shadow:0 0 40px rgba(56,156,255,.6); } .title h1 .q { color:#FF4063; text-shadow:0 0 40px rgba(255,64,99,.6); }
.title .tag { font:600 44px 'Saira'; color:#C9D3E4; }
.title .bullets { display:flex; gap:18px; margin-top:60px; }
.bullet { width:84px; height:84px; border-radius:12px; display:grid; place-items:center; font:800 40px 'Saira Condensed'; color:#fff; border:2px solid rgba(255,255,255,.25); }
.clock { background:linear-gradient(#1A2336,#0F1726); border:2px solid #34435E; color:#fff; padding:10px 28px; font:800 70px 'Saira Condensed'; font-variant-numeric:tabular-nums; letter-spacing:.04em; }
.tally { display:flex; }
.tally div { color:#fff; padding:10px 28px; font:800 46px 'Saira Condensed'; }
.tally .r { background:linear-gradient(#FF4063,#B81F3D); } .tally .b { background:linear-gradient(#389CFF,#1B5FA8); }
.panel { background:linear-gradient(180deg, rgba(20,29,46,.94), rgba(10,15,26,.94)); border:2px solid #34435E; border-left:8px solid #FF4063; padding:40px 44px; }
.panel .eyebrow { font:600 26px 'Saira'; letter-spacing:.3em; text-transform:uppercase; color:#8894AA; }
.panel h2 { font:900 96px 'Saira Condensed'; margin:0 0 16px; }
.panel .score { font:900 140px 'Saira Condensed'; line-height:1; }
.panel .score .r { color:#FF4063; text-shadow:0 0 30px rgba(255,64,99,.5); } .panel .score .b { color:#389CFF; text-shadow:0 0 30px rgba(56,156,255,.5); } .panel .score .x { color:#34435E; }
.tl .track { background:linear-gradient(90deg,#34435E,#5A6A88); height:4px; }
.td { width:30px; height:30px; border-radius:50%; }
.td.r { background:#FF4063; box-shadow:0 0 20px #FF4063; } .td.b { background:#389CFF; box-shadow:0 0 20px #389CFF; }
.tt { font:600 24px 'Saira'; color:#8894AA; } .tn { font:800 20px 'Saira Condensed'; color:#fff; }
.flag { border:2px solid #FF4063; color:#FF7A93; font:800 28px 'Saira Condensed'; padding:6px 14px; letter-spacing:.06em; text-transform:uppercase; }
.verdict { font:700 40px 'Saira'; } .verdict b { color:#FF4063; }
""",
}

BASE = """
* { box-sizing:border-box; margin:0; }
html, body { width:1920px; height:1080px; overflow:hidden; }
.stage { position:relative; width:1920px; height:1080px; }
.bullet.r { background:#C42847; } .bullet.b { background:#1D6FB8; }
.tl { position:relative; height:120px; margin-top:34px; }
.tl .track { position:absolute; left:0; right:0; top:52px; }
.td { position:absolute; top:55px; transform:translate(-50%,-50%); display:grid; place-items:center; }
.tt { position:absolute; top:-46px; white-space:nowrap; }
.tn { line-height:1; }
.flag { position:absolute; top:88px; transform:translateX(-10%); white-space:nowrap; }
"""

DEFS = """<svg width="0" height="0" style="position:absolute"><defs>
<filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="tile" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="0" flood-color="#000" flood-opacity=".35"/></filter>
</defs></svg>"""

def page(theme, body):
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{FONTS[theme]}&display=swap">
<style>{BASE}{CSS[theme]}</style></head><body>{DEFS}<div class="stage">{body}</div></body></html>"""

def title(theme):
    tilt = 'transform: perspective(1600px) rotateX(38deg) rotateZ(-8deg);' if theme == 'b' else ''
    extra = '<div class="bar"></div>' if theme == 'a' else ('<div class="fog"></div>' if theme == 'c' else '')
    return page(theme, f"""{extra}
<div class="table" style="position:absolute; right:70px; top:110px; width:860px; {tilt}">{svg_map(theme, scores='fill')}</div>
<div class="title" style="position:absolute; left:110px; top:230px; width:880px;">
  <div class="kicker">The rules, in two minutes</div>
  <h1><span class="c">CLIPPER</span><br><span class="q">CONQUEST</span></h1>
  <div class="tag">Tap on. Take over.</div>
  <div class="bullets"><div class="bullet r">R</div><div class="bullet b">B</div><div class="bullet" style="background:#444">41</div></div>
</div>""")

def tie(theme):
    tilt = 'transform: perspective(1600px) rotateX(34deg) rotateZ(-6deg);' if theme == 'b' else ''
    extra = '<div class="bar"></div>' if theme == 'a' else ('<div class="fog"></div>' if theme == 'c' else '')
    return page(theme, f"""{extra}
<div class="table" style="position:absolute; left:60px; top:150px; width:900px; {tilt}">{svg_map(theme, focus='Mission')}</div>
<div style="position:absolute; left:70px; top:{'40' if theme!='a' else '50'}px; display:flex; gap:20px; align-items:center;">
  <div class="clock">2:14:07</div>
  <div class="tally"><div class="r">RED {red}</div><div class="b">BLUE {blue}</div></div>
</div>
<div class="panel" style="position:absolute; right:70px; top:190px; width:720px;">
  <div class="eyebrow">Tie in the Mission</div>
  <h2>Mission</h2>
  <div class="score"><span class="r">2</span> <span class="x">–</span> <span class="b">2</span></div>
  {timeline()}
  <div class="verdict" style="margin-top:30px">Tied count? First to reach it holds. <b>Red keeps the Mission.</b></div>
</div>""")

os.makedirs(HERE, exist_ok=True)
for t in 'abc':
    open(os.path.join(HERE, f'{t}-title.html'), 'w').write(title(t))
    open(os.path.join(HERE, f'{t}-tie.html'), 'w').write(tie(t))
print('wrote 6 frames; red', red, 'blue', blue, 'H', round(H))
