"""The SF neighborhood map, projected into a 1000 x H box (y points down).

Shared by frames/build.py (the static scenes) and render/layers.py (the
animation layers). HOODS maps each neighborhood name to its SVG path 'd', its
projected 'rings', a label point 'c' (the most interior point of its largest
ring) and its bounding box 'bb' = (x0, y0, x1, y1).
"""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
geo = json.load(open(os.path.join(HERE, '../sf_neighborhoods.geojson')))


def rings(g):
    """The outer ring of each polygon in a GeoJSON (Multi)Polygon."""
    return [p[0] for p in g['coordinates']] if g['type'] == 'MultiPolygon' else [g['coordinates'][0]]


pts = [c for f in geo['features'] for r in rings(f['geometry']) for c in r]
lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
kx = math.cos(math.radians((lat0 + lat1) / 2))   # shrink longitude at SF's latitude
S = 1000 / ((lon1 - lon0) * kx)
H = (lat1 - lat0) * S


def P(c):
    """Project a (lon, lat) pair into map coordinates."""
    return ((c[0] - lon0) * kx * S, (lat1 - c[1]) * S)


def area(r):
    return 0.5 * sum(r[i-1][0]*r[i][1] - r[i][0]*r[i-1][1] for i in range(len(r)))


def inside(r, x, y):
    """Whether (x, y) is inside ring r (even-odd rule)."""
    c = False
    for i in range(len(r)):
        (x1, y1), (x2, y2) = r[i-1], r[i]
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c = not c
    return c


def segd(px, py, a, b):
    """Distance from (px, py) to the segment a-b."""
    (x1, y1), (x2, y2) = a, b; dx, dy = x2-x1, y2-y1
    t = max(0, min(1, ((px-x1)*dx+(py-y1)*dy)/((dx*dx+dy*dy) or 1)))
    return math.hypot(px-x1-t*dx, py-y1-t*dy)


def clearance(r, x, y):
    """Distance from (x, y) to the nearest edge of ring r."""
    return min(segd(x, y, r[k-1], r[k]) for k in range(len(r)))


def pole(r):
    """The point of a 40 x 40 grid over ring r that is farthest inside it."""
    xs, ys = [p[0] for p in r], [p[1] for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    best, bp = -1, (sum(xs)/len(xs), sum(ys)/len(ys))
    for i in range(40):
        for j in range(40):
            x = x0 + (x1-x0)*(i+.5)/40; y = y0 + (y1-y0)*(j+.5)/40
            if inside(r, x, y):
                d = clearance(r, x, y)
                if d > best: best, bp = d, (x, y)
    return bp


def zoom(n, pad):
    """A square viewBox (x, y, w, h) centered on neighborhood n, pad times its size."""
    x0, y0, x1, y1 = HOODS[n]['bb']; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = max(x1 - x0, y1 - y0) * pad
    return (cx - s / 2, cy - s / 2, s, s)


HOODS = {}
for f in geo['features']:
    rs = [[P(c) for c in r] for r in rings(f['geometry'])]
    d = ' '.join('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in r) + 'Z' for r in rs)
    big = max(rs, key=lambda r: abs(area(r)))
    xs, ys = [p[0] for r in rs for p in r], [p[1] for r in rs for p in r]
    HOODS[f['properties']['name']] = {'d': d, 'rings': rs, 'c': pole(big),
                                      'bb': (min(xs), min(ys), max(xs), max(ys))}
