#!/usr/bin/env python3
"""Build review_artifact.html — the claude.ai artifact page for remote challenge review.
Run from challenges/: python3 build_artifact.py   (then republish via the Artifact tool)
"""
import re, glob, html, json, math, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

order = json.load(open('../mockups/hood_order.json'))
pos = {n: i for i, n in enumerate(order)}

def parse_field(block, label):
    m = re.search(r'- \*\*' + label + r':\*\*\s*(.*?)(?=\n- \*\*|\Z)', block, re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''

def md_inline(s):
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'<i>\1</i>', s)
    return s

hoods = []
for fn in glob.glob('*.md'):
    if fn in ('BRIEF.md', 'QUEUE.md', 'DIGEST.md', 'JETLAG_EXAMPLES.md'): continue
    text = open(fn).read()
    name = re.match(r'# (.+)', text).group(1).strip()
    clean = re.sub(r'\s*\(.*\)', '', name)
    sketch_m = re.search(r'^# .+\n+(.+?)\n\n## Candidates', text, re.S)
    sketch = re.sub(r'\s+', ' ', sketch_m.group(1)) if sketch_m else ''
    cands = []
    for m in re.finditer(r'### (\d+)\.\s*(.+?)\n(.*?)(?=### \d+\.|## Recommended trio)', text, re.S):
        block = m.group(3)
        tc = parse_field(block, 'Time')
        tm = re.match(r'(.*?)\|\s*\*\*Cost:\*\*\s*(.*)', tc)
        cands.append({
            'title': m.group(2).strip(),
            'do': parse_field(block, 'Do'), 'where': parse_field(block, 'Where'),
            'time': tm.group(1).strip() if tm else tc,
            'cost': tm.group(2).strip() if tm else '',
            'fail': parse_field(block, 'Failable'), 'photo': parse_field(block, 'Photo'),
            'type': parse_field(block, 'Type') or 'Untagged',
        })
    trio_m = re.search(r'## Recommended trio\s*\n+\**([\d,\sand&]+)\**(.*)', text, re.S)
    trio = [int(x) for x in re.findall(r'\d+', trio_m.group(1))][:3]
    note = re.sub(r'\s+', ' ', trio_m.group(2)).strip(' —-*')
    hoods.append({'name': clean, 'sketch': sketch, 'cands': cands, 'trio': trio, 'note': note})

name_by_clean = {re.sub(r'\s*\(.*\)', '', o): o for o in order}
for h in hoods:
    h['num'] = pos[name_by_clean[h['name']]] + 1
    h['slug'] = re.sub(r'[^a-z0-9]+', '-', h['name'].lower()).strip('-')
hoods.sort(key=lambda h: h['num'])
slug_by_official = {name_by_clean[h['name']]: h['slug'] for h in hoods}

geo = json.load(open('../mockups/sf_neighborhoods.geojson'))
lons, lats = [], []
def walk(c):
    if isinstance(c[0], (int, float)): lons.append(c[0]); lats.append(c[1])
    else: [walk(x) for x in c]
for f in geo['features']: walk(f['geometry']['coordinates'])
kx = math.cos(math.radians((min(lats)+max(lats))/2))
S = 1000/((max(lons)-min(lons))*kx)
mnLon, mxLat = min(lons), max(lats)
P = lambda p: ((p[0]-mnLon)*kx*S, (mxLat-p[1])*S)

def inside(outers, x, y):
    cnt = 0
    for pts in outers:
        for i in range(len(pts)-1):
            (x1,y1),(x2,y2) = pts[i], pts[i+1]
            if (y1 <= y < y2) or (y2 <= y < y1):
                if x < x1 + (y-y1)*(x2-x1)/(y2-y1): cnt += 1
    return cnt % 2 == 1
def edge_dist(outers, x, y):
    best = 1e18
    for pts in outers:
        for i in range(len(pts)-1):
            (x1,y1),(x2,y2) = pts[i], pts[i+1]
            dx, dy = x2-x1, y2-y1
            L2 = dx*dx+dy*dy
            t = 0 if L2 == 0 else max(0.0, min(1.0, ((x-x1)*dx+(y-y1)*dy)/L2))
            d = math.hypot(x-(x1+t*dx), y-(y1+t*dy))
            if d < best: best = d
    return best
def polylabel(outers):
    xs = [p[0] for o in outers for p in o]; ys = [p[1] for o in outers for p in o]
    x0,x1,y0,y1 = min(xs),max(xs),min(ys),max(ys)
    best = None
    for gx in range(24):
        for gy in range(24):
            x = x0+(x1-x0)*(gx+.5)/24; y = y0+(y1-y0)*(gy+.5)/24
            if inside(outers,x,y):
                d = edge_dist(outers,x,y)
                if not best or d > best[0]: best = (d,x,y)
    d,bx,by = best
    step = max(x1-x0, y1-y0)/24
    for _ in range(4):
        step /= 2
        for ddx in (-step,0,step):
            for ddy in (-step,0,step):
                x,y = bx+ddx, by+ddy
                if inside(outers,x,y):
                    dd = edge_dist(outers,x,y)
                    if dd > d: d,bx,by = dd,x,y
    return bx,by

feats = sorted(geo['features'], key=lambda f: pos[f['properties']['name']])
map_parts = []
for idx, f in enumerate(feats, 1):
    official = f['properties']['name']
    slug = slug_by_official[official]
    geom = f['geometry']
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    outers = [[P(p) for p in poly[0]] for poly in polys]
    d = ''
    for poly in polys:
        for ring in poly:
            pts = [P(p) for p in ring]
            d += 'M' + 'L'.join(f'{x:.0f},{y:.0f}' for x, y in pts) + 'Z'
    ax, ay = polylabel(outers)
    map_parts.append(
        f'<a href="#{slug}" aria-label="{html.escape(official)}">'
        f'<path d="{d}"/>'
        f'<text x="{ax:.0f}" y="{ay+9:.0f}">{idx}</text></a>')
map_svg = ('<svg viewBox="0 0 1000 1000" class="jumpmap" role="navigation" '
           'aria-label="Tap a neighborhood to jump to its challenges" '
           'xmlns="http://www.w3.org/2000/svg">' + ''.join(map_parts) + '</svg>')

def fail_badge(f):
    fl = f.lower()
    if fl.startswith('no'): return ''
    if 'one-shot' in fl or 'one shot' in fl:
        return '<span class="badge oneshot">one-shot</span>'
    return '<span class="badge retry">retryable</span>'

sections, chips = [], []
n_cands = sum(len(h['cands']) for h in hoods)
from collections import Counter
trio_ct, all_ct = Counter(), Counter()
for h in hoods:
    for k, c in enumerate(h['cands'], 1):
        all_ct[c['type']] += 1
        if k in h['trio']: trio_ct[c['type']] += 1
fam_rows = ''.join(
    f'<tr><td>{html.escape(t)}</td><td>{trio_ct[t]}</td><td>{all_ct[t]}</td>'
    f'<td><i style="width:{100*trio_ct[t]/max(trio_ct.values())}%"></i></td></tr>'
    for t in sorted(all_ct, key=lambda t: (-trio_ct[t], -all_ct[t], t)))
fam_table = f'''<details class="fams" open><summary>Challenge types — {len(all_ct)} families</summary>
    <table><thead><tr><th>Family</th><th>Trio</th><th>All</th><th></th></tr></thead><tbody>{fam_rows}</tbody>
    <tfoot><tr><td>Total</td><td>{sum(trio_ct.values())}</td><td>{sum(all_ct.values())}</td><td></td></tr></tfoot></table>
    </details>'''
def type_chip(t): return f'<span class="type">{html.escape(t)}</span>'
for h in hoods:
    chips.append(f'<a href="#{h["slug"]}">{h["num"]} {html.escape(h["name"])}</a>')
    trio_html = []
    for tn in h['trio']:
        c = h['cands'][tn-1]
        meta = ' · '.join(x for x in (html.escape(c['time']), html.escape(c['cost'])) if x)
        trio_html.append(f'''<div class="chal">
      <div class="chal-head"><h3>{md_inline(c['title'])}</h3>{type_chip(c['type'])}{fail_badge(c['fail'])}</div>
      <p class="meta">{meta}</p>
      <p class="do">{md_inline(c['do'])}</p>
      <p class="where">📍 {md_inline(c['where'])}</p>
      <p class="photo">📷 {md_inline(c['photo'])}</p>
    </div>''')
    others = []
    for k, c in enumerate(h['cands'], 1):
        if k in h['trio']: continue
        others.append(f'<div class="alt"><b>{md_inline(c["title"])}</b>{type_chip(c["type"])}{fail_badge(c["fail"])}'
                      f'<span> — {md_inline(c["do"])}</span></div>')
    sections.append(f'''<section id="{h['slug']}">
    <h2><span class="hnum">{h['num']}</span>{html.escape(h['name'])}</h2>
    <p class="sketch">{md_inline(h['sketch'])}</p>
    {''.join(trio_html)}
    <p class="trionote">{md_inline(h['note'])}</p>
    <details><summary>Other candidates ({len(others)})</summary>{''.join(others)}</details>
    <p class="backtop"><a href="#top">↑ map</a></p>
  </section>''')

page = f'''<title>Clipper Conquest Challenges</title>
<style>
  :root {{
    --paper: #FFFFFF; --ink: #1C1E21; --muted: #64707B; --line: #E1E5E9;
    --card: #F6F8F9; --red: #C42847; --blue: #1D6FB8;
    --map-fill: #EDF0F2; --map-line: #FFFFFF;
    --oneshot-bg: #F9E4E8; --oneshot-ink: #A31F3B;
    --retry-bg: #FDF2DC; --retry-ink: #8A5A00;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --paper: #16181C; --ink: #E8EBEE; --muted: #98A2AC; --line: #2B3138;
      --card: #1E2126; --red: #E0526F; --blue: #5D9FD6;
      --map-fill: #23272D; --map-line: #16181C;
      --oneshot-bg: #3A2027; --oneshot-ink: #F2A0B2;
      --retry-bg: #38301C; --retry-ink: #E4B75E;
    }}
  }}
  :root[data-theme="dark"] {{
    --paper: #16181C; --ink: #E8EBEE; --muted: #98A2AC; --line: #2B3138;
    --card: #1E2126; --red: #E0526F; --blue: #5D9FD6;
    --map-fill: #23272D; --map-line: #16181C;
    --oneshot-bg: #3A2027; --oneshot-ink: #F2A0B2;
    --retry-bg: #38301C; --retry-ink: #E4B75E;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    background: var(--paper); color: var(--ink);
    font-family: system-ui, -apple-system, sans-serif;
    margin: 0; padding: 24px 18px 80px; line-height: 1.55;
  }}
  main {{ max-width: 640px; margin: 0 auto; }}
  header h1 {{ font-size: 27px; line-height: 1.15; margin: 0; text-wrap: balance; }}
  header h1 b {{ color: var(--red); }} header h1 i {{ color: var(--blue); font-style: normal; }}
  .stats {{ color: var(--muted); font-size: 14px; margin: 10px 0 14px; }}
  .jumpmap {{ width: 100%; height: auto; margin-bottom: 8px; }}
  .jumpmap path {{ fill: var(--map-fill); stroke: var(--map-line); stroke-width: 2.5; }}
  .jumpmap a {{ cursor: pointer; }}
  .jumpmap a:hover path, .jumpmap a:focus path {{ fill: var(--retry-bg); }}
  .jumpmap text {{
    font: 700 30px system-ui, sans-serif; fill: var(--ink);
    text-anchor: middle; pointer-events: none;
  }}
  nav {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }}
  nav a {{
    font-size: 12px; text-decoration: none; color: var(--ink);
    background: var(--card); border: 1px solid var(--line);
    border-radius: 999px; padding: 3px 10px;
  }}
  section {{ margin-top: 40px; scroll-margin-top: 12px; }}
  h2 {{ font-size: 20px; margin: 0 0 6px; display: flex; align-items: baseline; gap: 10px; }}
  .hnum {{ color: var(--red); font-size: 15px; font-variant-numeric: tabular-nums; }}
  .sketch {{ color: var(--muted); font-size: 13.5px; margin: 0 0 14px; }}
  .chal {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px;
           padding: 12px 14px; margin-bottom: 10px; }}
  .chal-head {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  h3 {{ font-size: 15.5px; margin: 0; }}
  .badge {{ font-size: 10.5px; font-weight: 600; border-radius: 999px; padding: 1px 8px; white-space: nowrap; }}
  .badge.oneshot {{ background: var(--oneshot-bg); color: var(--oneshot-ink); }}
  .badge.retry {{ background: var(--retry-bg); color: var(--retry-ink); }}
  .type {{ font-size: 10.5px; color: var(--muted); border: 1px solid var(--line); border-radius: 999px;
           padding: 1px 8px; white-space: nowrap; }}
  .alt .type {{ margin-left: 6px; }}
  .fams {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 10px 14px; margin: 0 0 16px; }}
  .fams summary {{ color: var(--ink); font-size: 14px; }}
  .fams table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; font-variant-numeric: tabular-nums; }}
  .fams th {{ text-align: left; color: var(--muted); font-weight: 500; font-size: 11.5px; text-transform: uppercase; letter-spacing: .06em; padding: 2px 6px 4px 0; }}
  .fams td {{ padding: 3px 6px 3px 0; border-top: 1px solid var(--line); }}
  .fams td:nth-child(2), .fams td:nth-child(3), .fams th:nth-child(2), .fams th:nth-child(3) {{ text-align: right; width: 3.2em; }}
  .fams td:last-child {{ width: 28%; padding-left: 10px; }}
  .fams td i {{ display: block; height: 8px; background: var(--blue); border-radius: 4px; }}
  .fams tfoot td {{ color: var(--muted); }}
  .meta {{ color: var(--muted); font-size: 12px; margin: 3px 0 8px; }}
  .do {{ font-size: 14px; margin: 0 0 8px; }}
  .where, .photo {{ color: var(--muted); font-size: 12.5px; margin: 0 0 4px; }}
  .trionote {{ color: var(--muted); font-size: 12.5px; font-style: italic; margin: 4px 0 10px; }}
  details {{ font-size: 13.5px; }}
  summary {{ cursor: pointer; color: var(--blue); font-weight: 600; font-size: 13px; }}
  .alt {{ margin: 10px 0; }}
  .alt span {{ color: var(--muted); }}
  .alt .badge {{ margin-left: 6px; }}
  .backtop {{ margin: 10px 0 0; font-size: 12px; }}
  .backtop a {{ color: var(--blue); text-decoration: none; }}
  footer {{ margin-top: 48px; color: var(--muted); font-size: 12.5px; border-top: 1px solid var(--line); padding-top: 14px; }}
</style>
<main id="top">
  <header>
    <h1><b>Clipper</b> <i>Conquest</i> — challenge review</h1>
    <p class="stats">{len(hoods)} neighborhoods · {n_cands} candidates · {len(hoods)*3} recommended.
    Tap the map or a chip to jump. Trio shown in full; alternates collapsed below each.</p>
  </header>
  {fam_table}
  {map_svg}
  <nav>{''.join(chips)}</nav>
  {''.join(sections)}
  <footer>Every candidate carries a type from the Jet Lag mechanic families (see the
  Jet Lag Mechanics page). Source of truth: challenges/*.md in the repo.</footer>
</main>
'''
open('review_artifact.html', 'w').write(page)
print('review_artifact.html:', len(page)//1024, 'KB,', len(hoods), 'hoods,', n_cands, 'candidates')
