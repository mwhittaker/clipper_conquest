#!/usr/bin/env python3
"""Render the v2 map's label placement to a PNG for visual review.

Replicates the anchor algorithm in v2.html (widest-chord rows scored toward
the vertical center, clearance checks, LABEL_TWEAKS). Keep SHORT/TWEAKS in
sync with v2.html when iterating. Output: /tmp/labels_render.png
Usage: python3 render_labels.py [zoom]   (zoom=1 default; e.g. 2 for a 2x view)
"""
import json, math, sys
from PIL import Image, ImageDraw, ImageFont

ZOOM = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
geo = json.load(open('sf_neighborhoods.geojson'))
lons, lats = [], []
def walk(c):
    if isinstance(c[0], (int, float)): lons.append(c[0]); lats.append(c[1])
    else: [walk(x) for x in c]
for f in geo['features']: walk(f['geometry']['coordinates'])
kx = math.cos(math.radians((min(lats)+max(lats))/2))
S = 1000/((max(lons)-min(lons))*kx)
mnLon, mxLat = min(lons), max(lats)
SC = 1.6 * ZOOM
P = lambda p: ((p[0]-mnLon)*kx*S*SC, (mxLat-p[1])*S*SC)

def chords(outers, y):
    best = None
    for pts in outers:
        xs = []
        for i in range(len(pts)-1):
            (x1,y1),(x2,y2) = pts[i], pts[i+1]
            if (y1 <= y < y2) or (y2 <= y < y1):
                xs.append(x1 + (y-y1)*(x2-x1)/(y2-y1))
        xs.sort()
        for i in range(0, len(xs)-1, 2):
            L = xs[i+1]-xs[i]
            if not best or L > best[0]: best = (L, (xs[i]+xs[i+1])/2)
    return best

def inside(outers, x, y):
    cnt = 0
    for pts in outers:
        for i in range(len(pts)-1):
            (x1,y1),(x2,y2) = pts[i], pts[i+1]
            if (y1 <= y < y2) or (y2 <= y < y1):
                if x < x1 + (y-y1)*(x2-x1)/(y2-y1): cnt += 1
    return cnt % 2 == 1

SHORT = {'Bayview Hunters Point':'Bayview','Castro/Upper Market':'Castro','Financial District/South Beach':'FiDi','Golden Gate Park':'GG Park','Haight Ashbury':'Haight','Hayes Valley':'Hayes','Lone Mountain/USF':'USF','McLaren Park':'McLaren','Oceanview/Merced/Ingleside':'OMI','Pacific Heights':'Pac Heights','Presidio Heights':'Presidio Hts','Potrero Hill':'Potrero','South of Market':'SoMa','Sunset/Parkside':'Sunset','Treasure Island':'Treasure Is','Visitacion Valley':'Vis Valley','West of Twin Peaks':'W Twin Peaks','Western Addition':'W Addition','Bernal Heights':'Bernal'}
TWEAKS = {'North Beach': (0, 10), 'Golden Gate Park': (70, 0)}
STATE = {'Marina':(3,0),'Inner Richmond':(2,0),'North Beach':(2,1),'Haight Ashbury':(1,0),'Mission':(1,2),'South of Market':(0,2),'Castro/Upper Market':(0,3),'Sunset/Parkside':(1,1),'Financial District/South Beach':(1,1)}
FOG, SURF, OPEN = (196,40,71), (29,111,184), (232,234,236)
SURF_HOODS = ('Mission','South of Market','Castro/Upper Market')

W = int(1600 * ZOOM)
img = Image.new('RGB', (W, W), (255,255,255))
dr = ImageDraw.Draw(img)
F = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
fmeas = ImageFont.truetype(F, 26)
fname = ImageFont.truetype(F, int(26*1.6))   # constant screen size at any zoom
fbadge = ImageFont.truetype(F, int(22*1.6))
def halo(x, y, txt, font, col):
    for ox, oy in ((-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,2),(-2,2),(2,-2)):
        dr.text((x+ox, y+oy), txt, font=font, fill=(30,30,30), anchor='ms')
    dr.text((x, y), txt, font=font, fill=col, anchor='ms')

k = 1.0 / ZOOM
feats = []
for f in geo['features']:
    name = f['properties']['name']
    geom = f['geometry']
    polys = [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']
    outers = [[P(p) for p in poly[0]] for poly in polys]
    st = STATE.get(name)
    fill = (SURF if name in SURF_HOODS else FOG) if st else OPEN
    for o in outers: dr.polygon([tuple(p) for p in o], fill=fill, outline=(255,255,255), width=2)
    feats.append((name, outers, st))

bad = 0
for name, outers, st in feats:
    ys = [p[1] for o in outers for p in o]
    mnY, mxY = min(ys), max(ys)
    flat = (mxY - mnY) < 60*SC
    bdy = (8 if flat else 17)*SC
    cand = []
    t = 0.18
    while t <= 0.821:
        y = mnY + (mxY-mnY)*t
        c = chords(outers, y)
        if c: cand.append((c[0]*(1-1.1*abs(t-0.47)), c[0], c[1], y))
        t += 0.04
    cand.sort(key=lambda c: -c[0])
    a = next((c for c in cand if inside(outers, c[2], c[3]-16*SC) and inside(outers, c[2], c[3]+bdy+4*SC)), cand[0])
    _, L, ax, ay = a
    if name in TWEAKS:
        ax += TWEAKS[name][0]*SC; ay += TWEAKS[name][1]*SC
    dy0 = next((v for v in (bdy/SC, 6, 4, 2, 0) if inside(outers, ax, ay+v*SC)), 0)
    for lbl, x, y in (('label', ax, ay-5*SC*k), ('badge', ax, ay+dy0*SC*k)):
        if not inside(outers, x, y): print('  OUTSIDE:', name, lbl); bad += 1
    short = SHORT.get(name, name)
    shown = dr.textlength(short, font=fmeas)*k < (L/SC)*0.88
    if shown and not (flat and st): halo(ax, ay-5*SC*k, short, fname, (255,255,255))
    if st: halo(ax, ay+dy0*SC*k, f'{st[0]}-{st[1]}', fbadge, (255,255,255))
img.save('/tmp/labels_render.png')
print('audit:', 'all inside' if not bad else f'{bad} OUTSIDE', '| wrote /tmp/labels_render.png')
