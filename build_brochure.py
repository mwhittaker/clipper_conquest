#!/usr/bin/env python3
"""Build brochure.html — the printable tri-fold (2 landscape Letter pages) that the guide's
"Print the brochure" button prints.

Inputs, all in this folder: sf_neighborhoods.geojson (the 41 neighborhoods),
muni_routes.geojson (the Muni overlay), challenges.json (the first three challenges, and the
neighborhood order) and rules.json. The QR code for the guide's public address is QR_GUIDE
below (make a new one with the qrcode library if the address ever changes).

Run:  python3 build_brochure.py     (then re-check print: headless Chrome to PDF, 2 pages)
"""
import json, math, re, glob, html, os, sys

_here = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(_here, 'brochure.html')
GUIDE_URL = 'https://mwhittaker.github.io/clipper_conquest/'
QR_GUIDE = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAASgAAAEoAQAAAADDfFG0AAAB9ElEQVR4nO1au47DMAwji/z/L/MGSnKCduhkqThruEsdAiUIm9ajFL6I1zeggzqot7gA+kkU4E8CQKjejGXfohdCJxGCVaKsXyo4lX2PXqA1EwkoRePtzVT2TXo56HPoYyj28voJFFn2hTiMI3hNQ0kpEeV9Jtj9481o9ltRF+qCXEHrVhfkWPb7UVynLvwLgPJDH6+pqMuS0f7uFCLuRv8VePKvFTYsWBdCDIUolpnNZd+CCn/33lIYV20zsYvXSFTuIZv7zeVFLQ+byn4/ChKUSX2teDlXpansm/IJURQRFSSr9FaczLHse1DhVZXaA5Hq2/fbeA1FeQ/JJRBXNwfIS2Ay+xZUHUH3KML3VQnsbPY7UelUlemXXCf/+hRRP2ZCr/T47CF6401l3+X3ikaEIIKQGzte6eM1ERX7S2Fh1bGHHSx8fyr7nnzV/5G96GqGOWGFTr66Yg2FVlFkG/OSEVPZN6GcfzHSMFfZZV4686FbUDFJW1sscvqYeBz/esSzvxoSVT8a0aSYyr7lfqw7MaWri/HUj2/xmG/LtkWGeEoVp7Lv0Wt1Cv0o1nOc16nsW1HRnFD1p+s3Ar/AfhPq9nsAUDkZWnOQU28/4wKqS+jhUNVFt6tzKvu2+hFY81rn+aGYy8qp7Fvzr03feFD/CfUHndb+J1KozkAAAAAASUVORK5CYII='   # a QR code for GUIDE_URL
os.chdir(_here)

# ---------- real challenge trios ----------
def plain(s):                 # drop **bold** / *italic* markers for the printed legend
    return re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', s).strip()
trios = {}
CHALLENGES = json.load(open('challenges.json', encoding='utf-8'))
for hood in CHALLENGES.values():
    trios[re.sub(r'\s*\(.*\)', '', hood['file_title']).lower()] = [plain(c['title']) for c in hood['candidates'][:3]]

# ---------- projection ----------
geo = json.load(open('sf_neighborhoods.geojson'))
muni = json.load(open('muni_routes.geojson'))
order = list(CHALLENGES)          # neighborhood numbering = the order of challenges.json
pos = {n: i for i, n in enumerate(order)}
lons, lats = [], []
def walk(c):
    if isinstance(c[0], (int, float)):
        lons.append(c[0]); lats.append(c[1])
    else:
        for x in c: walk(x)
for f in geo['features']: walk(f['geometry']['coordinates'])
kx = math.cos(math.radians((min(lats) + max(lats)) / 2))
S = 1000 / ((max(lons) - min(lons)) * kx)
mnLon, mxLat = min(lons), max(lats)
P = lambda p: ((p[0] - mnLon) * kx * S, (mxLat - p[1]) * S)

def chords(outers, y):
    best = None
    for pts in outers:
        xs = []
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            L = xs[i + 1] - xs[i]
            if not best or L > best[0]:
                best = (L, (xs[i] + xs[i + 1]) / 2)
    return best

def edge_dist(outers, x, y):
    best = 1e18
    for pts in outers:
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            dx, dy = x2 - x1, y2 - y1
            L2 = dx * dx + dy * dy
            t = 0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2))
            d = math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
            if d < best:
                best = d
    return best

def polylabel(outers):
    """Pole of inaccessibility: the interior point farthest from any boundary —
    the visual center a lone map number wants (chord rows suit label pairs)."""
    xs = [p[0] for o in outers for p in o]
    ys = [p[1] for o in outers for p in o]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    best = None
    for gx in range(24):
        for gy in range(24):
            x = x0 + (x1 - x0) * (gx + 0.5) / 24
            y = y0 + (y1 - y0) * (gy + 0.5) / 24
            if inside(outers, x, y):
                d = edge_dist(outers, x, y)
                if not best or d > best[0]:
                    best = (d, x, y)
    d, bx, by = best
    step = max(x1 - x0, y1 - y0) / 24
    for _ in range(4):
        step /= 2
        for ddx in (-step, 0, step):
            for ddy in (-step, 0, step):
                x, y = bx + ddx, by + ddy
                if inside(outers, x, y):
                    dd = edge_dist(outers, x, y)
                    if dd > d:
                        d, bx, by = dd, x, y
    return bx, by

def inside(outers, x, y):
    cnt = 0
    for pts in outers:
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            if (y1 <= y < y2) or (y2 <= y < y1):
                if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                    cnt += 1
    return cnt % 2 == 1

feats = sorted(geo['features'], key=lambda f: pos[f['properties']['name']])
hood_paths, numbers, legend = [], [], []
for idx, f in enumerate(feats, 1):
    name = f['properties']['name']
    geom = f['geometry']
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    outers = [[P(p) for p in poly[0]] for poly in polys]
    d = ''
    for poly in polys:
        for ring in poly:
            pts = [P(p) for p in ring]
            d += 'M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + 'Z'
    hood_paths.append(f'<path d="{d}" fill="#FFFFFF" stroke="#AAB2B9" stroke-width="1.4"/>')
    ax, ay = polylabel(outers)
    numbers.append(f'<text x="{ax:.0f}" y="{ay + 9:.0f}" text-anchor="middle" '
                   f'font-size="26" font-weight="700" fill="#1C1E21" '
                   f'stroke="#FFFFFF" stroke-width="7" paint-order="stroke">{idx}</text>')
    key = re.sub(r'\s*\(.*\)', '', name).lower()
    legend.append((idx, name, trios[key]))

muni_lines, routes = [], []
for f in muni['features']:
    p = f['properties']
    if p.get('mode') == 'local':
        continue   # brochure stays rail + rapid; locals live on the guide map
    coords = f['geometry']['coordinates']
    lines = [coords] if f['geometry']['type'] == 'LineString' else coords
    w = {'metro': 4, 'streetcar': 4, 'cable': 3}.get(p.get('mode'), 2.5)
    dash = ' stroke-dasharray="8 5"' if p.get('mode') == 'cable' else ''
    d = ''
    for line in lines:
        pts = [P(c) for c in line]
        d += 'M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    muni_lines.append(f'<path d="{d}" fill="none" stroke="{p.get("color", "#888")}" '
                      f'stroke-width="{w}" stroke-linecap="round" opacity="0.9"{dash}/>')
    routes.append((p.get('route', ''), p.get('name', ''), p.get('mode', ''), p.get('color', '#888')))

map_svg = ('<svg viewBox="0 0 1000 1000" xmlns="http://www.w3.org/2000/svg" '
           'preserveAspectRatio="xMidYMid meet" class="bmap">'
           + ''.join(hood_paths) + ''.join(muni_lines) + ''.join(numbers) + '</svg>')
cover_map = map_svg.replace('class="bmap"', 'class="covermap"')
qr = {'guide': QR_GUIDE}

def chips(mode):
    out = []
    for r, name, m, color in routes:
        if m != mode:
            continue
        short = name.split(' ', 1)[1] if ' ' in name else name
        out.append(f'<span class="line"><span class="chip" style="background:{color}"></span>'
                   f'<b>{html.escape(r)}</b> {html.escape(short)}</span>')
    return '\n'.join(out)

def trunc(s, n=34):
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'

legend_html = '\n'.join(
    f'<div class="lg"><b>{n}</b> <span class="hn">{html.escape(name)}</span>'
    + ''.join(f'<span class="ct">{html.escape(trunc(t))}</span>' for t in ch)
    + '</div>'
    for n, name, ch in legend)

_R = json.load(open('rules.json'))
RULES_LI = '\n'.join(f'      <li><b>{html.escape(b)}</b>{(" " + html.escape(t)) if t else ""}</li>' for b, t in _R['rules'])
RULES_INTRO = '\n'.join(f'    <p>{html.escape(p)}</p>' for p in _R['intro'])
RULES_ENC = f"<b>{html.escape(_R['encouraged'][0])}</b> {html.escape(_R['encouraged'][1])}"

page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Clipper Conquest — brochure</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap">
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  :root {{ --red: #C42847; --blue: #1D6FB8; --ink: #1C1E21; --muted: #6A7076; --line: #D9DDE1; }}
  body {{ font-family: Inter, system-ui, sans-serif; color: var(--ink); background: #EEF0F2; }}

  .screen-note {{ max-width: 900px; margin: 24px auto 0; padding: 0 16px; }}
  .screen-note h1 {{ font-size: 22px; }}
  .screen-note p {{ color: var(--muted); margin: 8px 0 4px; line-height: 1.5; }}
  .screen-note button {{
    font: inherit; font-size: 16px; font-weight: 600; margin: 12px 0 4px;
    padding: 10px 22px; border-radius: 8px; border: 1px solid var(--ink);
    background: var(--ink); color: #fff; cursor: pointer;
  }}
  .screen-note button:focus-visible {{ outline: 2px solid var(--ink); outline-offset: 2px; }}
  .sheet {{
    width: 11in; height: 8.5in; background: #fff; margin: 20px auto;
    box-shadow: 0 2px 14px rgba(0,0,0,.18); position: relative;
  }}

  .side {{ width: 11in; height: 8.5in; display: flex; overflow: hidden; position: relative; }}
  .panel {{ width: 3.6667in; height: 8.5in; padding: 0.42in 0.38in; position: relative; }}
  .panel + .panel {{ border-left: 1px dotted #C9CED3; }}

  .cover {{ display: flex; flex-direction: column; align-items: center; justify-content: center;
            text-align: center; padding-bottom: .7in; }}
  .covermap {{ width: 2.1in; height: 2.1in; margin-bottom: .05in; }}
  .covermap text {{ display: none; }}
  .cover h1 {{
    font-size: 34px; line-height: 1.04; letter-spacing: .01em;
    text-transform: uppercase; font-weight: 800; margin-top: .12in;
  }}
  .cover h1 .red {{ color: var(--red); }} .cover h1 .blue {{ color: var(--blue); }}
  .tagline {{ color: var(--muted); font-size: 12px; margin-top: .08in; }}
  .qrs {{ display: flex; gap: .3in; margin-top: .28in; }}
  .qrs figure {{ text-align: center; }}
  .qrs img {{ width: 1.05in; height: 1.05in; image-rendering: pixelated; }}
  .qrs figcaption {{ font-size: 9px; color: var(--muted); margin-top: 3px; }}
  .teamline {{ margin-top: .3in; font-size: 12px; color: var(--muted); }}
  .teamline b {{ color: var(--ink); }}

  .rules h2, .muni h2 {{ font-size: 16px; text-transform: uppercase; letter-spacing: .04em; margin-bottom: .12in; }}
  .rules p {{ font-size: var(--rs, 10.5px); line-height: 1.38; color: var(--muted); margin-bottom: .08in; }}
  .rules ol {{ padding-left: .18in; font-size: var(--rs, 10.5px); line-height: 1.38; }}
  .rules li {{ margin-bottom: .045in; }}

  .muni h3 {{ font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin: .14in 0 .05in; }}
  .line {{ display: flex; align-items: center; gap: 5px; font-size: 10px; margin: 2.5px 0; }}
  .line .chip {{ width: 16px; height: 8px; border-radius: 2px; flex: none; }}
  .notes {{ margin-top: .18in; border: 1px solid var(--line); border-radius: 6px; height: 1.5in; padding: 5px; }}
  .notes span {{ font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }}
  .clipper {{ font-size: 9.5px; color: var(--muted); margin-top: .12in; line-height: 1.4; }}

  .inside {{ padding: 0.3in; display: flex; gap: 0.22in; }}
  .mapwrap {{ flex: 1; display: flex; flex-direction: column; min-width: 0; }}
  .mapwrap h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: .05em; }}
  .bmap {{ flex: 1; width: 100%; min-height: 0; }}
  .lgcol {{ width: 5.35in; flex: none; display: flex; flex-direction: column; }}
  .lgcol h2 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .05em; margin-bottom: .07in; }}
  .lgs {{ column-count: 3; column-gap: .14in; flex: 1; min-height: 0; }}
  .lg {{ break-inside: avoid; margin-bottom: 3.5px; }}
  .lg b {{ font-size: 7.8px; color: var(--red); }}
  .lg .hn {{ font-size: 7.8px; font-weight: 700; }}
  .lg .ct {{ display: block; font-size: 7px; line-height: 1.26; color: #3A4148; padding-left: 9px; }}

  @media print {{
    @page {{ size: letter landscape; margin: 0; }}
    body {{ background: #fff; }}
    .screen-note {{ display: none; }}
    .sheet {{ box-shadow: none; margin: 0; page-break-after: always; }}
    .sheet:last-child {{ page-break-after: auto; }}
  }}
</style></head><body>

<div class="screen-note">
  <h1>Clipper Conquest — tri-fold brochure</h1>
  <p>Print double-sided on letter paper, <b>landscape, flip on short edge</b>, then Z-fold
  along the dotted guides with the cover facing out. Side 1 is the outside
  (Muni guide · rules · cover), side 2 is the map + challenge spread.</p>
  <button onclick="window.print()">Print brochure</button>
</div>

<div class="sheet">
<div class="side">
  <div class="panel muni">
    <h2>Getting around</h2>
    <h3>Metro rail</h3>
    {chips('metro')}
    <h3>Historic streetcar</h3>
    {chips('streetcar')}
    <h3>Cable cars (pricey — walk instead)</h3>
    {chips('cable')}
    <h3>Rapid buses</h3>
    {chips('rapid')}
    <p class="clipper">The game is named for the Clipper card — bring one (or a phone
    that taps). Muni only: Rapids and Muni Metro cross the city fastest; everything else is your feet.</p>
  </div>
  <div class="panel rules">
    <h2>How it works</h2>
{RULES_INTRO}
    <ol>
{RULES_LI}
    </ol>
    <p>{RULES_ENC}</p>
  </div>
  <div class="panel cover">
    {cover_map}
    <h1><span class="blue">Clipper</span><br><span class="red">Conquest</span></h1>
    <p class="tagline">Tap on. Take over.</p>
    <div class="qrs">
      <figure><img src="{qr['guide']}" alt="QR code for the study guide"><figcaption>Study guide<br>&amp; challenges</figcaption></figure>
    </div>
  </div>
</div>
</div>

<div class="sheet">
<div class="side inside">
  <div class="mapwrap">
    <h2>The board</h2>
    {map_svg}
  </div>
  <div class="lgcol">
    <h2>Neighborhoods &amp; their challenges</h2>
    <div class="lgs">
      {legend_html}
    </div>
  </div>
</div>
</div>

<script>
// system fonts differ between machines; if the rules still overflow their panel (say the web font
// failed to load), step the rules text down until everything fits. The guide waits on this before printing.
window.fitted = document.fonts.ready.then(() => {{
  const el = document.querySelector('.panel.rules');
  const over = () => {{ const lim = el.getBoundingClientRect().bottom - parseFloat(getComputedStyle(el).paddingBottom);
    return [...el.children].some(c => c.getBoundingClientRect().bottom > lim + 0.5); }};
  for (let s = 10.5; s > 7.5 && over(); s -= .25) el.style.setProperty('--rs', (s - .25) + 'px');
}});
</script>
</body></html>
'''
open(OUT_FILE, 'w').write(page)
print(os.path.relpath(OUT_FILE, _here), 'built:', len(page) // 1024, 'KB,', len(legend), 'hoods')
