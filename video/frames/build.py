#!/usr/bin/env python3
"""Storyboard frames for the rules video in the guide/app look (white, system type,
water-blue map panel, red #C42847 / blue #1D6FB8). Writes video/frames/NN-name.html;
screenshot each at 1920x1080 with headless Chrome.
"""
import json, os, sys, html
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from mapdata import HOODS, H, P

ROUTES = [f for f in json.load(open(os.path.join(HERE, '../../mockups/muni_routes.geojson')))['features']
          if f['properties']['mode'] != 'local']
QR = json.load(open(os.path.join(HERE, '../../mockups/qr_codes.json')))['guide']
CH = json.load(open(os.path.join(HERE, '../../mockups/challenges.json')))
ORDER = json.load(open(os.path.join(HERE, '../../mockups/hood_order.json')))
SHORT = {'Financial District/South Beach': 'FiDi', 'Castro/Upper Market': 'Castro',
         'Oceanview/Merced/Ingleside': 'OMI', 'Lone Mountain/USF': 'USF', 'Haight Ashbury': 'Haight',
         'Golden Gate Park': 'GG Park', 'Bayview Hunters Point': 'Bayview', 'Sunset/Parkside': 'Sunset',
         'West of Twin Peaks': 'W. Twin Peaks', 'Visitacion Valley': 'Vis Valley', 'South of Market': 'SoMa'}

# mid-game scenario: (red, blue) counts; holder by count, ties by who reached it first
MID = {
 'Mission': (0, 1, 'b'), 'Hayes Valley': (0, 3, 'b'), 'Western Addition': (0, 1, 'b'),
 'Haight Ashbury': (1, 0, 'r'), 'Castro/Upper Market': (2, 0, 'r'), 'Noe Valley': (1, 2, 'b'),
 'Bernal Heights': (3, 0, 'r'), 'Potrero Hill': (2, 1, 'r'), 'South of Market': (1, 2, 'b'),
 'Financial District/South Beach': (0, 2, 'b'), 'Chinatown': (0, 1, 'b'), 'North Beach': (2, 2, 'r'),
 'Nob Hill': (2, 0, 'r'), 'Tenderloin': (1, 0, 'r'), 'Russian Hill': (0, 2, 'b'),
 'Marina': (0, 1, 'b'), 'Pacific Heights': (1, 0, 'r'), 'Mission Bay': (0, 3, 'b'),
 'Inner Sunset': (2, 0, 'r'), 'Golden Gate Park': (1, 0, 'r'), 'Twin Peaks': (1, 0, 'r'),
 'Glen Park': (2, 1, 'r'), 'Japantown': (0, 1, 'b'), 'Lone Mountain/USF': (1, 0, 'r'),
}
END = dict(MID)
rest = [n for n in ORDER if n not in END]
for i, n in enumerate(rest):
    if i >= 12: break                        # 36 of 41 claimed by the end
    END[n] = (1, 0, 'r') if i % 2 == 0 else (0, 1, 'b')
END['Western Addition'] = (2, 1, 'r'); END['Chinatown'] = (2, 1, 'r')
tally = lambda S, t: sum(1 for v in S.values() if v[2] == t)

CSS = """
* { box-sizing:border-box; margin:0; }
html, body { width:1920px; height:1080px; overflow:hidden; background:#fff; color:#1C1E21;
  font-family:'Inter', system-ui, sans-serif; }
.stage { position:relative; width:1920px; height:1080px; }
.mapbox { position:absolute; background:#BFDDF3; border-radius:22px; overflow:hidden; }
.mapbox svg { width:100%; height:100%; display:block; }
.h { fill:#F1F2EE; stroke:#fff; stroke-width:1.6; vector-effect:non-scaling-stroke; }
.h.r { fill:#C42847; } .h.b { fill:#1D6FB8; }
.h.sel { fill:#FFD966; stroke:#1C1E21; stroke-width:4; }
.h.focus { stroke:#1C1E21; stroke-width:5; }
.h.dim { opacity:.55; }
.h.tie { fill:url(#tie); stroke:#1C1E21; stroke-width:5; }
.badge { font-weight:700; fill:#fff; paint-order:stroke; stroke:rgba(0,0,0,.45); stroke-linejoin:round;
  text-anchor:middle; dominant-baseline:central; }
.nm { font-weight:600; fill:#6A7076; paint-order:stroke; stroke:#F1F2EE; stroke-linejoin:round;
  text-anchor:middle; dominant-baseline:central; }
.bar { position:absolute; left:0; right:0; top:0; height:112px; display:flex; align-items:center;
  justify-content:space-between; padding:0 64px; border-bottom:1px solid #D9DDE1; }
.bar .team { font-size:44px; font-weight:800; display:flex; align-items:baseline; gap:14px; }
.bar .team small { font-size:22px; font-weight:600; color:#6A7076; letter-spacing:.04em; text-transform:uppercase; }
.bar .r { color:#C42847; } .bar .b { color:#1D6FB8; }
.bar .clock { font-size:52px; font-weight:800; font-variant-numeric:tabular-nums; letter-spacing:-.01em; }
.eyebrow { font-size:22px; color:#6A7076; letter-spacing:.08em; text-transform:uppercase; font-weight:600; }
.side { position:absolute; }
.side h2 { font-size:72px; font-weight:800; letter-spacing:-.02em; line-height:1.05; margin:6px 0 24px; }
.card { background:#F6F7F8; border:1px solid #D9DDE1; border-radius:18px; padding:22px 26px; margin-bottom:16px; }
.card .which { font-size:18px; color:#6A7076; text-transform:uppercase; letter-spacing:.06em; display:flex; gap:12px; align-items:center; }
.tag { text-transform:none; letter-spacing:0; font-size:17px; border:1px solid #D9DDE1; background:#fff; border-radius:999px; padding:1px 12px; }
.card .t { font-size:32px; font-weight:700; margin-top:6px; line-height:1.2; }
.card.done { background:#fff; }
.check { width:34px; height:34px; border-radius:50%; display:inline-grid; place-items:center; color:#fff; font-size:20px; font-weight:800; }
.check.r { background:#C42847; } .check.b { background:#1D6FB8; }
.feed .row { display:flex; gap:18px; align-items:center; padding:16px 0; border-bottom:1px solid #EEF0F2; font-size:30px; }
.feed .time { width:110px; color:#6A7076; font-variant-numeric:tabular-nums; font-weight:600; }
.feed .who.r { color:#C42847; font-weight:700; } .feed .who.b { color:#1D6FB8; font-weight:700; }
.feed .flip { background:#FFF6D6; border-radius:12px; padding:16px 14px; border-bottom:0; margin-top:6px; }
.score { font-size:150px; font-weight:800; letter-spacing:-.03em; line-height:1; }
.score .r { color:#C42847; } .score .b { color:#1D6FB8; } .score .x { color:#D9DDE1; }
.tl { position:relative; height:150px; margin:30px 0 10px; }
.tl .track { position:absolute; left:0; right:0; top:74px; height:6px; background:#D9DDE1; border-radius:3px; }
.tl .dot { position:absolute; top:77px; width:48px; height:48px; border-radius:50%; transform:translate(-50%,-50%);
  display:grid; place-items:center; color:#fff; font-weight:800; font-size:24px; border:5px solid #fff; }
.tl .dot.r { background:#C42847; } .tl .dot.b { background:#1D6FB8; }
.tl .tt { position:absolute; top:10px; transform:translateX(-50%); font-size:24px; color:#6A7076; font-weight:600; font-variant-numeric:tabular-nums; }
.tl .flag { position:absolute; top:112px; transform:translateX(-50%); font-size:24px; font-weight:700; background:#1C1E21; color:#fff; border-radius:10px; padding:6px 14px; white-space:nowrap; }
.verdict { font-size:44px; font-weight:700; line-height:1.25; }
.verdict b { color:#C42847; }
.legend .row { display:flex; align-items:center; gap:20px; font-size:32px; margin:18px 0; }
.chip { min-width:64px; height:64px; border-radius:32px; display:inline-grid; place-items:center; font-size:30px; font-weight:800; padding:0 16px; }
.big { font-size:120px; font-weight:800; letter-spacing:-.03em; line-height:1; }
"""
FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap">'
DEFS = ('<defs><pattern id="tie" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<rect width="14" height="28" fill="#C42847"/><rect x="14" width="14" height="28" fill="#1D6FB8"/></pattern></defs>')

def page(body):
    return f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body><div class="stage">{body}</div></body></html>'

def lock_glyph(x, y, h, color='#fff'):
    w = h * .78; bw, bh = w, h * .56; top = y - h / 2
    return (f'<path d="M{x - w*.3:.1f},{top + h*.46:.1f} v{-h*.14:.1f} a{w*.3:.1f},{w*.3:.1f} 0 0 1 {w*.6:.1f},0 v{h*.14:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{h*.11:.1f}"/>'
            f'<rect x="{x - bw/2:.1f}" y="{top + h*.44:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="{h*.08:.1f}" fill="{color}"/>')
LOCK_HTML = ('<svg viewBox="0 0 40 40" width="34" height="34">' + lock_glyph(20, 20, 30) + '</svg>')

def mapsvg(S=None, sel=None, focus=None, tie=None, dim=False, view=None, badges=True, names=(), steal=False, route=None, lab=1.0):
    S = S or {}
    vb = view or (-20, -20, 1040, H + 40)
    k = vb[2] / 1000                            # label scale with zoom
    out = [f'<svg viewBox="{vb[0]:.0f} {vb[1]:.0f} {vb[2]:.0f} {vb[3]:.0f}" preserveAspectRatio="xMidYMid meet">{DEFS}']
    for n, h in HOODS.items():
        c = 'h'
        if n in S: c += ' ' + S[n][2]
        if n == sel: c = 'h sel'
        if n == tie: c = 'h tie'
        if n == focus: c += ' focus'
        if dim and n not in (sel, focus, tie): c += ' dim'
        out.append(f'<path class="{c}" data-n="{html.escape(n)}" d="{h["d"]}"/>')
    if route:
        pts = ' '.join(f'{HOODS[n]["c"][0]:.0f},{HOODS[n]["c"][1]:.0f}' for n in route)
        out.append(f'<polyline points="{pts}" fill="none" stroke="#1C1E21" stroke-width="{7*k:.1f}" stroke-dasharray="{16*k:.0f} {12*k:.0f}" stroke-linecap="round" stroke-linejoin="round"/>')
    for n in names:
        x, y = HOODS[n]['c']
        out.append(f'<text class="nm" x="{x:.0f}" y="{y:.0f}" font-size="{30*k:.1f}" stroke-width="{6*k:.1f}">{html.escape(SHORT.get(n, n))}</text>')
    if badges:
        for n, (r, b, t) in S.items():
            x, y = HOODS[n]['c']
            if steal and t == 'b':
                cost = '🔒' if b == 3 else str(b + 1 - r)
                fill = '#1C1E21' if b == 3 else ('#FFD966' if b + 1 - r <= 2 else '#fff')
                ink = '#fff' if b == 3 else '#1C1E21'
                rr = 22 * k
                out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rr:.0f}" fill="{fill}" stroke="#1C1E21" stroke-width="{2.5*k:.1f}"/>'
                           + (lock_glyph(x, y, rr * 1.1) if b == 3 else f'<text x="{x:.0f}" y="{y:.0f}" font-size="{24*k:.0f}" font-weight="800" fill="{ink}" text-anchor="middle" dominant-baseline="central">{cost}</text>'))
            else:
                out.append(f'<text class="badge" x="{x:.0f}" y="{y:.0f}" font-size="{24*k*lab:.1f}" stroke-width="{5*k*lab:.1f}">{r}–{b}</text>')
    out.append('</svg>')
    return ''.join(out)

def routes_svg(hi=(), k=1.0):
    out = []
    for f in ROUTES:
        p = f['properties']; w = (9 if p['route'] in hi else 4.5) * k
        op = 1 if (not hi or p['route'] in hi) else .45
        for line in f['geometry']['coordinates']:
            pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (P(c) for c in line))
            out.append(f'<polyline points="{pts}" fill="none" stroke="{p["color"]}" stroke-width="{w:.1f}" '
                       f'stroke-linecap="round" stroke-linejoin="round" opacity="{op}"/>')
    return ''.join(out)

ALL_ROUTES = [f for f in json.load(open(os.path.join(HERE, '../../mockups/muni_routes.geojson')))['features']]
def locals_svg():
    out = []
    for f in ALL_ROUTES:
        if f['properties']['mode'] != 'local': continue
        for line in f['geometry']['coordinates']:
            pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (P(c) for c in line))
            out.append(f'<polyline points="{pts}" fill="none" stroke="#8C97A3" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" opacity=".55"/>')
    return ''.join(out)

def zoom(n, pad=1.9):
    x0, y0, x1, y1 = HOODS[n]['bb']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = max(x1 - x0, y1 - y0) * pad
    return (cx - s / 2, cy - s / 2, s, s)

def bar(S, clock):
    return (f'<div class="bar"><div class="team r">{tally(S,"r")} <small>Red</small></div>'
            f'<div class="clock">{clock}</div><div class="team b"><small>Blue</small> {tally(S,"b")}</div></div>')

FRAMES = {}

# 1. Title
FRAMES['01-title'] = page(f'''
<div class="side" style="left:110px; top:300px; width:760px">
  <div class="eyebrow">The rules in two minutes</div>
  <div style="font-size:150px; font-weight:800; letter-spacing:-.035em; line-height:.92; margin:22px 0 30px">
    <span style="color:#1D6FB8">Clipper</span><br><span style="color:#C42847">Conquest</span></div>
  <div style="font-size:44px; font-weight:600; color:#6A7076">Tap on. Take over.</div>
</div>
<div class="mapbox" style="left:930px; top:60px; width:900px; height:960px">{mapsvg(MID, badges=False)}</div>''')

# 2. Three challenges in North Beach
cards = ''.join(f'''<div class="card"><div class="which">Challenge {i+1} of 3 <span class="tag">{c["type"]}</span></div>
  <div class="t">{c["title"]}</div></div>''' for i, c in enumerate(CH['North Beach']))
FRAMES['02-challenges'] = page(f'''
<div class="mapbox" style="left:64px; top:64px; width:952px; height:952px">{mapsvg({}, sel='North Beach', view=zoom('North Beach', 2.6), badges=False, names=['North Beach','Chinatown','Russian Hill','Financial District/South Beach','Nob Hill','Marina'])}</div>
<div class="side" style="left:1090px; top:150px; width:760px">
  <div class="eyebrow">Neighborhood {ORDER.index("North Beach")+1} of 41</div>
  <h2>North Beach</h2>{cards}
  <div style="font-size:28px; color:#6A7076; margin-top:22px">Every neighborhood has 3 unique challenges.</div>
</div>''')

# 3. The flip: Red takes North Beach 2–1
S3 = {'North Beach': (2, 1, 'r')}
FRAMES['05-flip'] = page(f'''{bar(MID, "4:27:12")}
<div class="mapbox" style="left:64px; top:150px; width:880px; height:880px">{mapsvg(S3, focus='North Beach', view=zoom('North Beach', 2.4), lab=3.2, names=['Chinatown','Russian Hill','Financial District/South Beach','Nob Hill'])}</div>
<div class="side feed" style="left:1020px; top:170px; width:840px">
  <div class="eyebrow">North Beach · timeline</div>
  <div class="row"><span class="time">11:04</span><span class="check b">✓</span><span><span class="who b">The blue team</span> completes a challenge</span></div>
  <div class="row"><span class="time">11:40</span><span class="check r">✓</span><span><span class="who r">The red team</span> completes a challenge</span></div>
  <div class="row"><span class="time">11:58</span><span class="check r">✓</span><span><span class="who r">The red team</span> completes another</span></div>
  <div class="row flip"><span class="time">11:58</span><span style="font-weight:700">2–1 · <span class="who r">The red team steals North Beach</span></span></div>
  <div class="verdict" style="margin-top:40px">Complete more than the other team<br>and you <span style="color:#C42847">steal it.</span></div>
</div>''')

# 4. Tiebreak
def x(t, t0=11*60, t1=13*60): h, m = map(int, t.split(':')); return 5 + 90 * ((h*60+m) - t0) / (t1 - t0)
EV = [('b', '11:04', 1), ('r', '11:40', 1), ('r', '11:58', 2), ('b', '12:30', 2)]
tl = ''.join(f'<div class="tt" style="left:{x(t):.1f}%">{t}</div><div class="dot {c}" style="left:{x(t):.1f}%">{n}</div>' for c, t, n in EV)
FRAMES['06-tiebreak'] = page(f'''{bar(MID, "4:02:45")}
<div class="mapbox" style="left:64px; top:150px; width:880px; height:880px">{mapsvg({'North Beach': (2, 2, 't')}, tie='North Beach', view=zoom('North Beach', 2.4), lab=3.2, names=['Chinatown','Russian Hill','Financial District/South Beach','Nob Hill'])}</div>
<div class="side" style="left:1020px; top:180px; width:840px">
  <div class="eyebrow">Tie in North Beach</div>
  <div class="score" style="margin-top:14px"><span class="r">2</span> <span class="x">–</span> <span class="b">2</span></div>
  <div class="tl"><div class="track"></div>{tl}<div class="flag" style="left:{x("11:58"):.1f}%">The red team reaches 2 first</div></div>
  <div class="verdict" style="margin-top:40px">Ties go to whoever got there first.<br><b>The red team keeps North Beach.</b></div>
</div>''')

# 5. Steal costs
FRAMES['07-steal'] = page(f'''{bar(MID, "2:14:07")}
<div class="mapbox" style="left:64px; top:150px; width:1000px; height:880px">{mapsvg(MID, steal=True, route=['Western Addition','Japantown','Pacific Heights','Marina'])}</div>
<div class="side legend" style="left:1130px; top:190px; width:720px">
  <div class="eyebrow">Two ways to play</div>
  <h2 style="font-size:64px">Quick, or locked?</h2>
  <div class="row"><span class="chip" style="background:#C42847; border:5px solid #fff; box-shadow:0 0 0 2px #C42847; min-width:44px; height:44px; padding:0"></span>
    <span><b style="color:#C42847">The red team</b> does one challenge each. Fast, but easy to steal.</span></div>
  <div class="row"><span class="chip" style="background:#1C1E21; color:#fff">{LOCK_HTML}</span>
    <span><b style="color:#1D6FB8">The blue team</b> does all three. Slow, but locked for good.</span></div>
</div>''')

# 3. Muni only
def muni_map():
    base = mapsvg({}, badges=False)
    # team dot on the 14R near North Beach's center
    r14 = next(f for f in ROUTES if f['properties']['route'] == 'PM')
    mx, my = HOODS['North Beach']['c']
    dx, dy = min((P(c) for line in r14['geometry']['coordinates'] for c in line), key=lambda q: (q[0]-mx)**2 + (q[1]-my)**2)
    extra = locals_svg() + routes_svg(hi=('PM', 'F')) + (f'<circle cx="{dx:.0f}" cy="{dy:.0f}" r="20" fill="#C42847" stroke="#fff" stroke-width="6"/>')
    return base.replace('</svg>', extra + '</svg>')
FRAMES['03-muni'] = page(f'''{bar(MID, "5:12:40")}
<div class="mapbox" style="left:64px; top:150px; width:1000px; height:880px">{muni_map()}</div>
<div class="side legend" style="left:1130px; top:210px; width:720px">
  <div class="eyebrow">Getting around</div>
  <h2 style="font-size:84px">Muni only.</h2>
  <div class="row"><span class="chip" style="background:#1C1E21; color:#fff">✓</span> Buses, Metro, streetcars, cable cars</div>
  <div class="row"><span class="chip" style="background:#fff; border:3px solid #C42847; color:#C42847">✕</span> No BART, no Caltrain</div>
  <div class="row"><span class="chip" style="background:#fff; border:3px solid #C42847; color:#C42847">✕</span> No cars, no bikes</div>
  <div class="row" style="color:#6A7076; font-size:30px; margin-top:34px">And no running — speedwalk.</div>
</div>''')

# 4. Photo proof in the app
MURAL = '''<svg viewBox="0 0 600 420" style="width:100%; display:block; border-radius:14px">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8EC5EC"/><stop offset="1" stop-color="#D8ECF8"/></linearGradient></defs>
<rect width="600" height="420" fill="url(#sky)"/>
<circle cx="110" cy="90" r="34" fill="#FFF6D6"/>
<path d="M0 330 C120 250 220 215 300 212 C390 210 480 250 600 320 V420 H0 Z" fill="#5E9E5A"/>
<path d="M0 360 C150 320 250 300 330 300 C430 300 520 330 600 360 V420 H0 Z" fill="#437D45"/>
<rect x="276" y="92" width="48" height="126" fill="#F4F1EA"/>
<g stroke="#D9D2C3" stroke-width="3">
<line x1="284" y1="100" x2="284" y2="214"/><line x1="292" y1="100" x2="292" y2="214"/><line x1="300" y1="100" x2="300" y2="214"/>
<line x1="308" y1="100" x2="308" y2="214"/><line x1="316" y1="100" x2="316" y2="214"/></g>
<rect x="268" y="84" width="64" height="12" fill="#EDE8DD"/>
<rect x="280" y="64" width="40" height="22" fill="#F4F1EA"/>
<g fill="#6F7A86"><rect x="284" y="68" width="6" height="12"/><rect x="297" y="68" width="6" height="12"/><rect x="310" y="68" width="6" height="12"/></g>
<rect x="262" y="214" width="76" height="10" fill="#EDE8DD"/>
<circle cx="200" cy="232" r="26" fill="#3F7A3F"/><circle cx="228" cy="226" r="20" fill="#4C8A4A"/>
<circle cx="382" cy="236" r="24" fill="#3F7A3F"/><circle cx="408" cy="244" r="18" fill="#4C8A4A"/>
</svg>'''
def phone(done):
    photo = MURAL if done else ('<div style="height:295px; border-radius:14px; background:#1C1E21; display:grid; place-items:center; color:#fff; font-size:24px; font-weight:700">'
             '<div style="text-align:center"><div style="width:84px; height:84px; border-radius:50%; border:6px solid #fff; margin:0 auto 14px"></div>Take photo</div></div>')
    btn = ('<div style="margin-top:18px; background:#C42847; color:#fff; border-radius:16px; padding:18px; text-align:center; font-size:26px; font-weight:800">✓ Completed · 11:58</div>'
           '<div style="margin-top:14px; font-size:16px; color:#6A7076">Uploading photo… 72%</div>'
           '<div style="height:10px; border-radius:5px; background:#E8EAEC; margin-top:6px"><div style="width:72%; height:100%; border-radius:5px; background:#C42847"></div></div>') if done else \
          ('<div style="margin-top:18px; background:#C42847; color:#fff; border-radius:16px; padding:18px; text-align:center; font-size:26px; font-weight:800">Complete</div>'
           '<div style="margin-top:14px; font-size:16px; color:#6A7076">Red team · photo required</div>')
    return f'''<div class="phone" style="position:absolute; left:250px; top:40px; width:520px; height:1000px; border-radius:64px; background:#1C1E21; padding:18px;
  box-shadow:0 30px 60px rgba(28,30,33,.25)">
 <div style="width:100%; height:100%; border-radius:48px; background:#fff; overflow:hidden; font-family:Inter,system-ui,sans-serif">
  <div style="display:flex; justify-content:space-between; align-items:center; padding:46px 28px 14px; border-bottom:1px solid #D9DDE1">
    <b style="color:#C42847; font-size:30px">13</b><b style="font-size:30px; font-variant-numeric:tabular-nums">4:27:12</b><b style="color:#1D6FB8; font-size:30px">11</b></div>
  <div style="padding:20px 26px">
   <div style="font-size:15px; color:#6A7076; letter-spacing:.06em; text-transform:uppercase">North Beach · Challenge 3 of 3</div>
   <div style="font-size:32px; font-weight:800; margin:6px 0 10px">{CH['North Beach'][2]['title']}</div>
   <div style="font-size:17px; color:#3A4148; line-height:1.45; margin-bottom:16px">Get to Coit Tower. That's it — the hill is the challenge.</div>
   {photo}
   {btn}
  </div></div></div>'''
FRAMES['04-photo'] = page(f'''{phone(True)}
<div class="side legend" style="left:960px; top:250px; width:880px">
  <div class="eyebrow">Proof</div>
  <h2 style="font-size:84px">Every completion<br>needs a photo.</h2>
  <div class="row"><span class="chip" style="background:#1C1E21; color:#fff">1</span> Finish the challenge, snap the photo</div>
  <div class="row"><span class="chip" style="background:#1C1E21; color:#fff">2</span> Log it in the app — that time counts</div>
  </div>''')

# 8. Close
FRAMES['08-end'] = page(f'''
<div class="side" style="left:110px; top:280px; width:900px">
  <div style="font-size:150px; font-weight:800; letter-spacing:-.035em; line-height:.92; margin-bottom:30px">
    <span style="color:#1D6FB8">Clipper</span><br><span style="color:#C42847">Conquest</span></div>
  <div style="font-size:44px; font-weight:600; color:#6A7076">Tap on. Take over.</div>
</div>
<div class="side" style="left:1180px; top:250px; width:560px; text-align:center">
  <img src="{QR}" style="width:420px; height:420px; image-rendering:pixelated; border:1px solid #D9DDE1; border-radius:18px; padding:20px">
  <div style="font-size:32px; font-weight:700; margin-top:22px">Every rule and every challenge:</div>
  <div style="font-size:32px; color:#6A7076">the guide</div>
</div>''')


# ================= full storyboard: one frame per beat =================
NEIGH = ['Chinatown','Russian Hill','Financial District/South Beach','Nob Hill']
def mission(S, rows, verdict, clock, tie=False, flip=False):
    feed = ''.join(
        (f'<div class="row flip"><span class="time">{t}</span><span style="font-weight:700">{txt}</span></div>' if kind == 'flip' else
         f'<div class="row"><span class="time">{t}</span><span class="check {kind}">✓</span><span>{txt}</span></div>')
        for t, kind, txt in rows) or '<div class="row" style="color:#6A7076">No challenges logged yet</div>'
    m = mapsvg({'North Beach': S} if S else {}, focus=None if tie else 'North Beach', tie='North Beach' if tie else None,
               view=zoom('North Beach', 2.4), lab=3.2, names=NEIGH, badges=True) if S else \
        mapsvg({}, focus='North Beach', view=zoom('North Beach', 2.4), names=NEIGH + ['North Beach'], badges=False)
    return page(f"""{bar(MID, clock)}
<div class="mapbox" style="left:64px; top:150px; width:880px; height:880px">{m}</div>
<div class="side feed" style="left:1020px; top:170px; width:840px">
  <div class="eyebrow">North Beach · timeline</div>{feed}
  <div class="verdict" style="margin-top:40px">{verdict}</div></div>""")
B = lambda w: f'<span class="who b">The blue team</span> {w}'
R = lambda w: f'<span class="who r">The red team</span> {w}'

def outlines(frac):
    names = list(HOODS)[:int(len(HOODS) * frac)]
    paths = ''.join(f'<path d="{HOODS[n]["d"]}" fill="none" stroke="#1C1E21" stroke-width="2.2" vector-effect="non-scaling-stroke"/>' for n in names)
    return f'<svg viewBox="-20 -20 1040 {H+40:.0f}">{paths}</svg>'

SB = {}
def tri(cx, cy, w, up=True):
    h = w * .82
    return (f'<polygon points="{cx:.1f},{cy - h/2:.1f} {cx + w/2:.1f},{cy + h/2:.1f} {cx - w/2:.1f},{cy + h/2:.1f}"/>' if up else
            f'<polygon points="{cx - w/2:.1f},{cy - h/2:.1f} {cx + w/2:.1f},{cy - h/2:.1f} {cx:.1f},{cy + h/2:.1f}"/>')
def clipper_mark(fill='#fff'):
    # the Clipper triangle stack, in a 200x320 card coordinate space
    return (f'<g fill="{fill}">' + tri(70, 110, 16) + tri(70, 127, 20) + tri(68, 149, 30) + tri(64, 177, 34, False)
            + tri(108, 117, 18) + tri(106, 140, 28) + tri(104, 168, 40) + tri(100, 214, 60, False) + '</g>')
CARD_SVG = f"""<svg viewBox="0 0 200 320" width="150" height="240"><defs>
<linearGradient id="ctop" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2F63AE"/><stop offset="1" stop-color="#1B3F86"/></linearGradient>
<linearGradient id="cbot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2D72BC"/><stop offset="1" stop-color="#1A4A94"/></linearGradient>
<clipPath id="cr"><rect width="200" height="320" rx="14"/></clipPath></defs>
<g clip-path="url(#cr)"><rect width="200" height="186" fill="url(#ctop)"/><rect y="186" width="200" height="134" fill="url(#cbot)"/>
<rect width="200" height="320" fill="url(#shine)" opacity="0"/></g>
{clipper_mark()}
<text x="20" y="298" fill="#fff" font-size="21" font-weight="800" font-family="Inter,system-ui,sans-serif" letter-spacing=".5">CLIPPER</text>
<text x="112" y="290" fill="#fff" font-size="6" font-weight="700" font-family="Inter,system-ui,sans-serif">SM</text></svg>"""
READER_SVG = f"""<svg viewBox="0 0 460 1040" width="460" height="1040"><defs>
<linearGradient id="steel" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8E959C"/><stop offset=".14" stop-color="#D6D9DC"/>
 <stop offset=".5" stop-color="#BFC4C8"/><stop offset=".86" stop-color="#DFE2E4"/><stop offset="1" stop-color="#8C9399"/></linearGradient>
<linearGradient id="hood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#737A82"/><stop offset="1" stop-color="#4B5158"/></linearGradient>
<linearGradient id="face" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2E3237"/><stop offset=".25" stop-color="#454A51"/><stop offset="1" stop-color="#383C42"/></linearGradient>
<linearGradient id="disp" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2A7FD0"/><stop offset="1" stop-color="#1B62AE"/></linearGradient></defs>
<path d="M30,1040 V200 A200,180 0 0 1 430,200 V1040 Z" fill="url(#steel)"/>
<path d="M30,300 V200 A200,180 0 0 1 430,200 V300 H384 V214 A154,140 0 0 0 76,214 V300 Z" fill="url(#hood)"/>
<g transform="translate(142,40) scale(.36)">{clipper_mark()}</g>
<text x="200" y="104" fill="#fff" font-size="25" font-weight="800" font-family="Inter,system-ui,sans-serif">CLIPPER</text>
<rect x="96" y="150" width="268" height="450" rx="8" fill="url(#face)"/>
<rect x="148" y="214" width="164" height="220" rx="18" fill="#0D1115"/>
<rect x="160" y="228" width="140" height="192" rx="7" fill="url(#disp)"/>
<g id="scr-idle" font-family="Inter,system-ui,sans-serif" font-weight="800" fill="#fff" text-anchor="middle">
 <text x="230" y="306" font-size="26">TAP</text><text x="230" y="338" font-size="26">CARD</text>
 <path d="M214 374 l16 -14 l16 14" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></g>
<g id="scr-ok" opacity="0" font-family="Inter,system-ui,sans-serif" font-weight="800" fill="#fff" text-anchor="middle">
 <text x="230" y="282" font-size="25">TRAVEL</text><text x="230" y="312" font-size="25">OK</text>
 <circle cx="230" cy="362" r="27" fill="none" stroke="#fff" stroke-width="4.5"/>
 <path id="okcheck" d="M216 362 l9 10 l19 -21" fill="none" stroke="#fff" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/></g>
<rect x="183" y="456" width="94" height="50" rx="7" fill="#1E2226"/>
<text x="230" y="489" fill="#fff" font-size="23" font-weight="600" font-family="Inter,system-ui,sans-serif" text-anchor="middle">&#x2038;TAG</text>
<g fill="#24282C">{''.join(f'<circle cx="{194 + 9*i}" cy="{528 + 9*j}" r="2.2"/>' for i in range(9) for j in range(6))}</g>
<rect x="108" y="614" width="244" height="426" fill="#C7CBCF" stroke="#8F959B" stroke-width="2"/>
<rect x="126" y="640" width="208" height="84" rx="8" fill="#1F2A56"/>
<rect x="126" y="716" width="208" height="84" fill="#2F86D1"/>
<rect x="126" y="800" width="208" height="84" fill="#1F2A56"/>
<rect x="126" y="884" width="208" height="84" rx="8" fill="#2F86D1"/><rect x="126" y="884" width="208" height="10" fill="#2F86D1"/>
<g font-family="Inter,system-ui,sans-serif" font-weight="800" fill="#fff" text-anchor="middle">
 <text x="230" y="678" font-size="25">TAP ON.</text><text x="230" y="708" font-size="25">TAP OFF.</text>
 <text x="230" y="752" font-size="17">TOCA PARA SUBIR.</text><text x="230" y="778" font-size="17">TOCA PARA BAJAR.</text>
 <text x="230" y="838" font-size="25">TAP ON.</text><text x="230" y="868" font-size="25">TAP OFF.</text>
 <text x="230" y="920" font-size="17">TOCA PARA SUBIR.</text><text x="230" y="946" font-size="17">TOCA PARA BAJAR.</text></g>
<rect x="176" y="992" width="108" height="26" rx="3" fill="#E4E6E8" stroke="#9AA0A6"/>
<text x="230" y="1010" font-size="13" fill="#555B61" font-family="Inter,system-ui,sans-serif" text-anchor="middle">MUNI-4402</text></svg>"""
SPARK_COLORS = ['#C42847', '#1D6FB8', '#FFD966', '#2F86D1', '#F2B233', '#C42847']
SPARKS = ''.join(f'<div class="spark" style="position:absolute; left:960px; top:350px; width:0; height:0">'
                 f'<svg viewBox="-10 -10 20 20" width="{26 + (i*7) % 22}" height="{26 + (i*7) % 22}" style="position:absolute; left:-18px; top:-18px">'
                 f'<path d="M0,-10 C1.5,-2 2,-1.5 10,0 C2,1.5 1.5,2 0,10 C-1.5,2 -2,1.5 -10,0 C-2,-1.5 -1.5,-2 0,-10Z" fill="{SPARK_COLORS[i % 6]}"/></svg></div>'
                 for i in range(22))
RINGS = ''.join(f'<div class="ring" style="position:absolute; left:960px; top:350px; width:0; height:0; border-radius:50%; border:6px solid #2F86D1; opacity:0"></div>' for _ in range(3))
SB['0-tap'] = page(f"""
<div style="position:absolute; inset:0; background:radial-gradient(ellipse 55% 60% at 50% 45%, #EAF3FB 0%, #fff 70%)"></div>
<div id="reader" style="position:absolute; left:730px; top:24px; width:460px; height:1040px">{READER_SVG}</div>
{RINGS}{SPARKS}
<div id="eraser" style="position:absolute; top:0; bottom:0; left:1920px; right:0; background:#fff"></div>
<div id="card" style="position:absolute; left:0; top:0; width:150px; height:240px; filter:drop-shadow(0 26px 30px rgba(28,30,33,.28));
  transform:translate(1160px,330px) rotate(8deg)">{CARD_SVG}</div>""")

SB['1a-draw'] = page(f'<div style="position:absolute; left:460px; top:60px; width:1000px; height:960px">{outlines(1.0)}</div>')
SB['1b-title'] = FRAMES['01-title']
SB['2a-grey'] = page(f"""<div class="mapbox" style="left:64px; top:64px; width:1000px; height:952px">{mapsvg({}, badges=False)}</div>
<div class="side" style="left:1130px; top:300px; width:720px">
  <div class="big" style="font-size:180px">41</div>
  <div class="verdict" style="margin-top:8px">neighborhoods.<br><span style="color:#6A7076">Most neighborhoods when the clock hits zero wins.</span></div></div>""")
SB['2b-challenges'] = FRAMES['02-challenges']
SB['3a-muni'] = FRAMES['03-muni']
SB['4a-phone'] = page(f"""{phone(False)}
<div class="side legend" style="left:960px; top:330px; width:880px">
  <div class="eyebrow">Proof</div><h2 style="font-size:84px">Snap it.</h2>
  <div class="row" style="color:#6A7076">Every completion needs a photo.</div></div>""")
SB['4b-upload'] = FRAMES['04-photo']
SB['5a-empty'] = mission(None, [], 'Complete its challenges<br>to conquer it.', '4:52:00')
SB['5b-blue'] = mission((0, 1, 'b'), [('11:04', 'b', B('completes a challenge'))], 'North Beach is<br><span style="color:#1D6FB8">the blue team\'s.</span>', '4:48:21')
SB['5c-tied1'] = mission((1, 1, 'b'), [('11:04', 'b', B('completes a challenge')), ('11:40', 'r', R('completes a challenge'))], 'The red team is on the board…', '4:31:44')
SB['5d-flip'] = FRAMES['05-flip']
SB['5e-tie2'] = mission((2, 2, 't'), [('11:04', 'b', B('completes a challenge')), ('11:40', 'r', R('completes a challenge')),
                                        ('11:58', 'r', R('completes another')), ('12:30', 'b', B('completes another'))],
                        'Two–two. So who holds it?', '3:57:10', tie=True)
SB['6a-tiebreak'] = FRAMES['06-tiebreak']
HAY = [('10:12', 'b', B('completes a challenge')), ('10:31', 'b', B('completes another')), ('10:50', 'b', B('completes the third'))]
def hayes_map():
    m = mapsvg({'Hayes Valley': (0, 3, 'b')}, focus='Hayes Valley', view=zoom('Hayes Valley', 2.6), lab=2.6, badges=False,
               names=['Western Addition','Haight Ashbury','Mission','South of Market','Tenderloin','Castro/Upper Market'])
    x, y = HOODS['Hayes Valley']['c']; vb = zoom('Hayes Valley', 2.6); k = vb[2] / 1000
    return m.replace('</svg>', '<g class="lockpop" style="transform-box:fill-box; transform-origin:center">'
                               f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{56*k:.0f}" fill="#1C1E21"/>'
                               + lock_glyph(x, y, 60*k) + '</g></svg>')
SB['6b-sweep'] = page(f"""{bar(MID, "3:40:02")}
<div class="mapbox" style="left:64px; top:150px; width:880px; height:880px">{hayes_map()}</div>
<div class="side feed" style="left:1020px; top:170px; width:840px">
  <div class="eyebrow">Hayes Valley · timeline</div>
  {''.join(f'<div class="row"><span class="time">{t}</span><span class="check {k}">✓</span><span>{w}</span></div>' for t, k, w in HAY)}
  <div class="row flip"><span class="time">10:50</span><span style="font-weight:700">3 for 3 — <span class="who b">locked for good</span></span></div>
  <div class="verdict" style="margin-top:40px">All three: locked.<br><span style="color:#6A7076">Safe — but it takes a while.</span></div></div>""")
SB['7a-costs'] = FRAMES['07-steal']
AFTER = dict(MID); AFTER.update({'Western Addition': (2, 1, 'r'), 'Japantown': (2, 1, 'r'), 'Marina': (2, 1, 'r')})
m7 = mapsvg(AFTER, steal=True, route=['Western Addition','Japantown','Pacific Heights','Marina'])
m7 = m7.replace('stroke="#1C1E21" stroke-width', 'stroke="#C42847" stroke-width', 1)
_unused_7b = page(f"""{bar(AFTER, "1:31:55")}
<div class="mapbox" style="left:64px; top:150px; width:1000px; height:880px">{m7}</div>
<div class="side legend" style="left:1130px; top:260px; width:720px">
  <div class="eyebrow">An hour later</div><h2 style="font-size:72px">Three steals.<br>Six challenges.</h2>
  <div class="row" style="color:#6A7076">Western Addition, Japantown and the Marina flip to Red.</div>
  <div class="row" style="color:#6A7076">Every one they held with a single challenge.</div></div>""")
SB['8a-end'] = FRAMES['08-end']
FRAMES = SB
for name, doc in FRAMES.items():
    open(os.path.join(HERE, name + '.html'), 'w').write(doc)
print('frames:', ', '.join(FRAMES), '| mid', tally(MID, 'r'), tally(MID, 'b'), '| end', tally(END, 'r'), tally(END, 'b'))
