"""Shared map data for video frames: SF neighborhoods projected into a 1000 x H box."""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
geo = json.load(open(os.path.join(HERE, '../mockups/sf_neighborhoods.geojson')))

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
    allp = [p for r in rs for p in r]
    HOODS[f['properties']['name']] = {'d': d, 'c': pole(big), 'bb': (min(p[0] for p in allp), min(p[1] for p in allp), max(p[0] for p in allp), max(p[1] for p in allp))}

