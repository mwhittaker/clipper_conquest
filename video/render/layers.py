"""Continuous animation layers that sit above the beat scenes and keep running across
beat changes: the title/"41 neighborhoods" conquest simulation, the handheld Coit Tower
photo, team dots doing challenges in North Beach and Hayes Valley, and the strategy
race. build(timeline, captions) returns (html, css, js, events) for render/build.py.
All motion is a pure function of t so every frame renders deterministically.
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from mapdata import HOODS, H, inside, clearance, zoom

RED, BLUE, LAND, WATER, INK = '#C42847', '#1D6FB8', '#F1F2EE', '#BFDDF3', '#1C1E21'
CONFETTI_COLORS = ['#C42847', '#1D6FB8', '#FFD966', '#2F86D1', '#F2B233', '#fff']


def interior_points(n, k=3, avoid=0):
    """k well-separated interior points of neighborhood n, west to east, each at least
    `avoid` from its label point (where the score badge sits)."""
    r = max(HOODS[n]['rings'], key=len); x0, y0, x1, y1 = HOODS[n]['bb']
    cx, cy = HOODS[n]['c']
    cands = []
    for i in range(60):
        for j in range(60):
            x = x0 + (x1 - x0) * (i + .5) / 60; y = y0 + (y1 - y0) * (j + .5) / 60
            if inside(r, x, y) and math.hypot(x - cx, y - cy) > avoid:
                cands.append((x, y, clearance(r, x, y)))
    cands.sort(key=lambda c: c[0])
    out = []
    for q in range(k):                                    # best-clearance point in each slice
        sl = cands[int(len(cands) * q / k): int(len(cands) * (q + 1) / k)]
        x, y, _ = max(sl, key=lambda c: c[2]); out.append([round(x, 1), round(y, 1)])
    return out


def map_svg(view, cls=''):
    paths = ''.join(f'<path class="lh" data-n="{n}" d="{h["d"]}"/>' for n, h in HOODS.items())
    return (f'<svg class="lmap {cls}" viewBox="{view_box(view)}" preserveAspectRatio="xMidYMid meet">'
            f'{paths}<g class="lfx"></g></svg>')


def view_box(view):
    return ' '.join(f'{v:.1f}' for v in view)


def dots_svg(view):
    """An empty svg over a zoomed map scene, for the team dots of runLegs()."""
    return f'<svg viewBox="{view_box(view)}" preserveAspectRatio="xMidYMid meet"><g class="dots"></g></svg>'

COIT = '''<svg viewBox="0 0 600 680" preserveAspectRatio="xMidYMid slice" class="coit">
<defs><linearGradient id="csky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7DB9E8"/><stop offset="1" stop-color="#D9ECF8"/></linearGradient></defs>
<rect width="600" height="680" fill="url(#csky)"/>
<circle cx="480" cy="120" r="46" fill="#FFF3C9"/>
<ellipse cx="130" cy="150" rx="70" ry="18" fill="#fff" opacity=".8"/><ellipse cx="190" cy="140" rx="46" ry="14" fill="#fff" opacity=".8"/>
<path d="M0 470 C120 380 220 330 300 326 C390 324 480 380 600 450 V680 H0 Z" fill="#5E9E5A"/>
<path d="M0 520 C150 470 250 450 330 452 C430 452 520 490 600 520 V680 H0 Z" fill="#437D45"/>
<rect x="268" y="150" width="64" height="176" fill="#F4F1EA"/>
<g stroke="#D9D2C3" stroke-width="3.5"><line x1="279" y1="160" x2="279" y2="322"/><line x1="290" y1="160" x2="290" y2="322"/><line x1="300" y1="160" x2="300" y2="322"/>
<line x1="310" y1="160" x2="310" y2="322"/><line x1="321" y1="160" x2="321" y2="322"/></g>
<rect x="258" y="138" width="84" height="16" fill="#EDE8DD"/><rect x="274" y="110" width="52" height="30" fill="#F4F1EA"/>
<g fill="#6F7A86"><rect x="279" y="116" width="8" height="16"/><rect x="296" y="116" width="8" height="16"/><rect x="313" y="116" width="8" height="16"/></g>
<rect x="248" y="322" width="104" height="14" fill="#EDE8DD"/>
<circle cx="190" cy="350" r="34" fill="#3F7A3F"/><circle cx="226" cy="342" r="26" fill="#4C8A4A"/><circle cx="160" cy="366" r="24" fill="#4C8A4A"/>
<circle cx="398" cy="352" r="30" fill="#3F7A3F"/><circle cx="432" cy="364" r="22" fill="#4C8A4A"/>
<path d="M0 600 C200 580 400 590 600 575 V680 H0Z" fill="#3A6E3C"/></svg>'''

LOCK_AT = 5.4   # seconds into the Hayes Valley beat (6b-sweep) when the third check lands and the lock pops


def zero_offset(c2):
    """Seconds after the 2a-grey voiceover starts when the game clock hits zero: most of the way
    through its second caption. render/build.py holds the beat long enough for the finale after it."""
    return c2[1][0] + .72 * (c2[1][1] - c2[1][0]) if len(c2) > 1 else 8


def build(tl, caps):
    B = {b['id']: b for b in tl}
    ev = {}
    # --- title + 41 neighborhoods: continuous conquest sim ---
    s1, s2 = B['1b-title'], B['2a-grey']
    c2 = caps.get('2a-grey', [])
    zero = s2['vo'] + zero_offset(c2)
    sim = {
        'T0': s1['start'] + .7, 'TZ': round(zero, 3), 'start': s1['start'], 'slide': s2['start'], 'end': s2['start'] + s2['dur'],
        'r1': [930, 60, 900, 960], 'r2': [64, 64, 1000, 952],
        'route': {
            'r': ['Financial District/South Beach', 'North Beach', 'Russian Hill', 'Nob Hill', 'Tenderloin', 'South of Market', 'Mission',
                  'Castro/Upper Market', 'Haight Ashbury', 'Lone Mountain/USF', 'Inner Richmond', 'Outer Richmond', 'Lincoln Park',
                  'Seacliff', 'Presidio', 'Marina', 'Pacific Heights', 'Presidio Heights'],
            'b': ['Financial District/South Beach', 'South of Market', 'Mission Bay', 'Potrero Hill', 'Bayview Hunters Point', 'Bernal Heights',
                  'Mission', 'Noe Valley', 'Castro/Upper Market', 'Glen Park', 'Excelsior', 'Portola', 'Visitacion Valley', 'McLaren Park',
                  'Outer Mission', 'Oceanview/Merced/Ingleside', 'Lakeshore', 'Sunset/Parkside', 'Inner Sunset', 'Golden Gate Park']},
    }
    ev['win'] = sim['TZ']
    # --- handheld photo ---
    a, b4 = B['4a-phone'], B['4b-upload']
    ca, cb = caps.get('4a-phone', [[0, 2.2]]), caps.get('4b-upload', [[0, 1.6]])
    s4 = b4['start']
    phone = {'start': a['start'], 'end': s4 + b4['dur'], 'shutter': round(a['vo'] + ca[0][1] - .15, 3),
             'app': s4, 'addTap': s4 + .55, 'sheetUp': s4 + .65, 'pick': s4 + 1.5, 'sheetDown': s4 + 1.75, 'upStart': s4 + 2.1, 'upEnd': s4 + 2.9}
    phone['tap'] = round(max(b4['vo'] + cb[0][1] - .2, phone['upEnd'] + .2), 3)
    ev['shutter'], ev['tap'] = phone['shutter'], phone['tap']
    # --- North Beach walk-through: dots enter, do challenges, leave ---
    S = {k: B[k]['start'] for k in ('5a-empty', '5b-blue', '5c-tied1', '5d-flip', '5e-tie2', '6a-tiebreak')}
    nbv = zoom('North Beach', 2.4); spA, spB, spC = interior_points('North Beach', 3, avoid=nbv[2] * .09)  # west→east
    E, W = nbv[0] + nbv[2] + 60, nbv[0] - 60
    nb = {'view': nbv, 'start': S['5a-empty'], 'end': S['6a-tiebreak'] + .45, 'r': nbv[2] * .026, 'legs': [
        # team, path points, times (arrive/leave at each point), challenge completions
        {'team': 'b', 'pts': [[E, spC[1]], spC, [E, spC[1] + 40]], 'times': [S['5a-empty'] + .5, S['5a-empty'] + 1.5, S['5b-blue'] + .7, S['5b-blue'] + 1.8],
         'done': [S['5b-blue'] + .2]},
        {'team': 'r', 'pts': [[W, spB[1]], spB, spA, [W, spA[1] - 40]],
         'times': [S['5c-tied1'] + 2.6, S['5c-tied1'] + 3.6, S['5c-tied1'] + 5.0, S['5c-tied1'] + 6.2, S['5d-flip'] + .6, S['5d-flip'] + 1.7],
         'done': [S['5c-tied1'] + 4.6, S['5d-flip'] + .2]},
        {'team': 'b', 'pts': [[E, spB[1] + 30], spB, [E, spB[1] - 20]], 'times': [S['5d-flip'] + 1.9, S['5d-flip'] + 2.9, S['5e-tie2'] + .7, S['5e-tie2'] + 1.8],
         'done': [S['5e-tie2'] + .2]}]}
    c6 = caps.get('6a-tiebreak', [])
    nb['resolve'] = round(B['6a-tiebreak']['vo'] + (c6[-1][0] if c6 else 5.0), 3)   # "So the red team keeps North Beach."
    ev['resolve'] = nb['resolve']
    # --- Hayes Valley lock ---
    s6 = B['6b-sweep']['start']; hv = zoom('Hayes Valley', 2.6); h1, h2, h3 = interior_points('Hayes Valley', 3, avoid=hv[2] * .05)
    top = hv[1] - 60
    hay = {'view': hv, 'start': s6, 'end': s6 + B['6b-sweep']['dur'] + .3, 'r': hv[2] * .026, 'lock': s6 + LOCK_AT, 'fill': s6 + 1.2,
           'legs': [{'team': 'b', 'pts': [[h1[0], top], h1, h2, h3, [h3[0] + 30, top]],
                     'times': [s6 + .1, s6 + .8, s6 + 1.4, s6 + 2.1, s6 + 3.0, s6 + 3.7, s6 + 5.8, s6 + 6.8],
                     'done': [s6 + 1.2, s6 + 2.8, s6 + 4.4]}]}
    ev['lock'] = hay['lock']
    # --- strategy race ---
    s7 = B['7a-costs']
    strat = {'start': s7['start'], 'end': s7['start'] + s7['dur'] + .45, 'T0': s7['start'] + .7, 'rect': [64, 150, 1000, 880],
             'red': ['Sunset/Parkside', 'Inner Sunset', 'Golden Gate Park', 'Outer Richmond', 'Inner Richmond', 'Lone Mountain/USF',
                     'Haight Ashbury', 'Twin Peaks', 'West of Twin Peaks', 'Oceanview/Merced/Ingleside', 'Lakeshore', 'Excelsior',
                     'Glen Park', 'Castro/Upper Market', 'Noe Valley'],
             'blue': ['Chinatown', 'North Beach', 'Russian Hill', 'Nob Hill', 'Financial District/South Beach']}
    PTS = {n: [round(h['c'][0], 1), round(h['c'][1], 1)] for n, h in HOODS.items()}
    data = {'sim': sim, 'phone': phone, 'nb': nb, 'hay': hay, 'strat': strat, 'PTS': PTS}

    confetti = ''.join(f'<i style="background:{CONFETTI_COLORS[i % 6]}"></i>' for i in range(110))
    full = [-20, -20, 1040, H + 40]
    html = f'''
<div id="L-sim" class="layer"><div class="lbox">{map_svg(full)}
  <div class="pill"><b class="pr">0</b><span class="pc">6:00:00</span><b class="pb">0</b></div>
  <div class="winner"></div></div></div>
<div id="L-confetti" class="layer">{confetti}</div>
<div id="L-phone" class="layer"><div class="coitbg">{COIT}</div>
  <div class="ph"><div class="ph-scr">
    <div class="cam"><div class="cam-top"><span>HDR</span><span>&#9679; LIVE</span></div>
      <div class="vf"><div class="vf-live">{COIT}</div><div class="vf-grid"></div><div class="vf-flash"></div></div>
      <div class="cam-bot"><div class="cam-mode">PHOTO</div><div class="cam-roll"><div class="cam-roll-img">{COIT}</div></div>
        <div class="vf-btn"><i></i></div><div class="cam-flip"></div></div></div>
    <div class="app">
      <div class="ph-top"><b style="color:{RED}">13</b><b>4:27:12</b><b style="color:{BLUE}">11</b></div>
      <div class="ph-body"><div class="ph-lab">North Beach · Challenge 3 of 3</div><div class="ph-title">Get to Coit Tower</div>
        <div class="slot"><div class="slot-empty"><b>+</b><span>Add photo</span></div><div class="slot-img">{COIT}</div>
          <div class="up"><div class="up-bar"><i></i></div><span class="up-txt">Uploading…</span></div></div>
        <div class="ph-btn">Complete</div></div>
      <div class="sheet"><div class="sheet-grab"></div><div class="sheet-title">Recents</div>
        <div class="grid"><div class="th pick">{COIT}<div class="pick-chk">&#10003;</div></div><div class="th" style="background:#E9C46A"></div><div class="th" style="background:#8AB17D"></div><div class="th" style="background:#E76F51"></div><div class="th" style="background:#7FA7C9"></div><div class="th" style="background:#B5838D"></div><div class="th" style="background:#6D8A96"></div><div class="th" style="background:#F4A261"></div><div class="th" style="background:#9C89B8"></div></div></div>
      <div class="tapfx"></div></div>
  </div></div></div>
<div id="L-nb" class="layer zoomlayer">{dots_svg(nbv)}</div>
<div id="L-hay" class="layer zoomlayer">{dots_svg(hv)}</div>
<div id="L-strat" class="layer"><div class="lbox" style="left:64px; top:150px; width:1000px; height:880px">{map_svg(full)}
  <div class="pill"><b class="pr">0</b><span class="pc">3:10:00</span><b class="pb">0</b></div></div></div>'''

    css = f'''
.layer {{ position:absolute; inset:0; pointer-events:none; opacity:0; z-index:40; }}
.lbox {{ position:absolute; background:{WATER}; border-radius:22px; overflow:hidden; }}
.lmap {{ width:100%; height:100%; display:block; }}
.lh {{ fill:{LAND}; stroke:#fff; stroke-width:1.6; vector-effect:non-scaling-stroke; }}
.pill {{ position:absolute; left:50%; top:22px; transform:translateX(-50%); background:#fff; border-radius:999px; padding:10px 26px;
  display:flex; gap:26px; align-items:baseline; box-shadow:0 8px 24px rgba(28,30,33,.16); font-family:Inter,system-ui,sans-serif; }}
.pill b {{ font-size:40px; font-weight:800; font-variant-numeric:tabular-nums; display:inline-block; min-width:44px; text-align:center; }}
.pill .pr {{ color:{RED}; }} .pill .pb {{ color:{BLUE}; }}
.pill .pc {{ font-size:34px; font-weight:800; color:{INK}; font-variant-numeric:tabular-nums; }}
.winner {{ position:absolute; left:50%; top:112px; transform:translateX(-50%) scale(0); color:#fff; font:800 40px Inter,system-ui,sans-serif;
  padding:10px 28px; border-radius:16px; white-space:nowrap; box-shadow:0 10px 26px rgba(28,30,33,.2); }}
#L-confetti {{ z-index:60; }}
#L-confetti i {{ position:absolute; left:0; top:0; width:12px; height:20px; border-radius:2px; }}
.zoomlayer svg {{ position:absolute; left:64px; top:150px; width:880px; height:880px; }}
.coitbg {{ position:absolute; left:64px; top:64px; width:880px; height:952px; border-radius:22px; overflow:hidden; }}
.coitbg svg, .vf-live svg {{ width:100%; height:100%; display:block; }}
.ph {{ position:absolute; left:300px; top:120px; width:430px; height:880px; border-radius:62px; background:#1C1E21; padding:16px;
  box-shadow:0 40px 70px rgba(28,30,33,.35); transform-origin:50% 90%; }}
.ph-scr {{ width:100%; height:100%; border-radius:48px; background:#fff; overflow:hidden; font-family:Inter,system-ui,sans-serif; position:relative; }}
.ph-top {{ display:flex; justify-content:space-between; padding:42px 30px 12px; border-bottom:1px solid #D9DDE1; font-size:26px; font-variant-numeric:tabular-nums; }}
.ph-body {{ padding:16px 22px; position:relative; }}
.ph-lab {{ font-size:14px; color:#6A7076; letter-spacing:.06em; text-transform:uppercase; }}
.ph-title {{ font-size:30px; font-weight:800; margin:4px 0 14px; }}
.cam, .app {{ position:absolute; inset:0; }}
.cam {{ background:#000; color:#fff; }}
.cam-top {{ display:flex; justify-content:space-between; padding:40px 34px 10px; font-size:16px; font-weight:700; letter-spacing:.06em; color:#FFD34D; }}
.vf {{ position:absolute; left:0; right:0; top:84px; height:560px; overflow:hidden; background:#000; }}
.vf-live {{ position:absolute; left:-30%; top:-20%; width:160%; height:140%; }}
.vf-grid {{ position:absolute; inset:0; background:
  linear-gradient(90deg, transparent 33.1%, rgba(255,255,255,.35) 33.3%, transparent 33.5%, transparent 66.5%, rgba(255,255,255,.35) 66.7%, transparent 66.9%),
  linear-gradient(0deg, transparent 33.1%, rgba(255,255,255,.35) 33.3%, transparent 33.5%, transparent 66.5%, rgba(255,255,255,.35) 66.7%, transparent 66.9%); }}
.vf-flash {{ position:absolute; inset:0; background:#fff; opacity:0; }}
.cam-bot {{ position:absolute; left:0; right:0; bottom:0; height:204px; }}
.cam-mode {{ text-align:center; color:#FFD34D; font-size:17px; font-weight:800; letter-spacing:.14em; margin-top:18px; }}
.vf-btn {{ position:absolute; left:50%; top:64px; width:88px; height:88px; margin-left:-44px; border-radius:50%; border:6px solid #fff; display:grid; place-items:center; }}
.vf-btn i {{ width:68px; height:68px; border-radius:50%; background:#fff; display:block; }}
.cam-roll {{ position:absolute; left:40px; top:78px; width:62px; height:62px; border-radius:12px; overflow:hidden; background:#222; border:2px solid #555; }}
.cam-roll-img {{ width:100%; height:100%; opacity:0; }}
.cam-flip {{ position:absolute; right:40px; top:80px; width:58px; height:58px; border-radius:50%; background:#2A2A2A; }}
.app {{ background:#fff; opacity:0; }}
.ph-btn {{ margin-top:16px; border-radius:16px; padding:18px; text-align:center; font-size:26px; font-weight:800; background:#E8EAEC; color:#9AA1AB; }}
.slot {{ position:relative; height:320px; border-radius:16px; overflow:hidden; border:3px dashed #C9CED4; background:#F6F7F8; }}
.slot-empty {{ position:absolute; inset:0; display:grid; place-content:center; justify-items:center; gap:6px; color:#6A7076; font-size:22px; font-weight:700; }}
.slot-empty b {{ font-size:54px; line-height:1; color:#1D6FB8; }}
.slot-img {{ position:absolute; inset:0; opacity:0; }}
.up {{ position:absolute; left:14px; right:14px; bottom:14px; background:rgba(255,255,255,.92); border-radius:12px; padding:10px 14px; opacity:0; }}
.up-bar {{ height:8px; border-radius:4px; background:#E8EAEC; overflow:hidden; }} .up-bar i {{ display:block; height:100%; width:0; background:#C42847; }}
.up-txt {{ display:block; margin-top:6px; font-size:16px; font-weight:700; color:#1C1E21; }}
.sheet {{ position:absolute; left:0; right:0; bottom:0; height:540px; background:#fff; border-radius:28px 28px 0 0; box-shadow:0 -12px 30px rgba(28,30,33,.25);
  transform:translateY(110%); padding:14px 16px; }}
.sheet-grab {{ width:60px; height:6px; border-radius:3px; background:#D9DDE1; margin:0 auto 12px; }}
.sheet-title {{ font-size:24px; font-weight:800; margin:0 4px 12px; }}
.grid {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; }}
.th {{ aspect-ratio:1; border-radius:6px; overflow:hidden; position:relative; }}
.th svg {{ width:100%; height:100%; display:block; }}
.pick-chk {{ position:absolute; right:8px; bottom:8px; width:34px; height:34px; border-radius:50%; background:#1D6FB8; color:#fff; border:3px solid #fff;
  display:grid; place-items:center; font-size:18px; font-weight:800; opacity:0; }}
.th.pick {{ outline:0 solid #1D6FB8; outline-offset:-5px; }}
.tapfx {{ position:absolute; width:64px; height:64px; margin:-32px 0 0 -32px; border-radius:50%; background:rgba(28,30,33,.28); opacity:0; }}
[data-id="1b-title"] .mapbox, [data-id="2a-grey"] .mapbox, [data-id="7a-costs"] .mapbox, [data-id="4a-phone"] .phone, [data-id="4b-upload"] .phone {{ display:none; }}
'''
    js = JS.replace('__L__', json.dumps(data))
    return html, css, js, ev

JS = r'''
const L = __L__;
const $ = (s, r = document) => r.querySelector(s), NS = 'http://www.w3.org/2000/svg';
const COL = { r: '#C42847', b: '#1D6FB8' };
const LOCK = (x, y, h) => { const w = h * .78, top = y - h / 2;
  return `<path d="M${x - w * .3},${top + h * .46} v${-h * .14} a${w * .3},${w * .3} 0 0 1 ${w * .6},0 v${h * .14}" fill="none" stroke="#fff" stroke-width="${h * .11}"/>` +
         `<rect x="${x - w / 2}" y="${top + h * .44}" width="${w}" height="${h * .56}" rx="${h * .08}" fill="#fff"/>`; };
function mkDot(g, team, r) {
  const grp = document.createElementNS(NS, 'g');
  grp.innerHTML = `<circle class="ring" r="${r}" fill="none" stroke="${COL[team]}" stroke-width="${r * .22}" opacity="0"/>` +
    `<path class="arc" fill="none" stroke="${COL[team]}" stroke-width="${r * .28}" stroke-linecap="round"/>` +
    `<circle class="body" r="${r}" fill="${COL[team]}" stroke="#fff" stroke-width="${r * .32}" style="filter:drop-shadow(0 3px 4px rgba(28,30,33,.45))"/>` +
    `<g class="chk" opacity="0"><circle r="${r * .9}" fill="#fff" stroke="${COL[team]}" stroke-width="${r * .18}"/>` +
    `<path d="M${-r * .4},0 l${r * .28},${r * .3} l${r * .52},${-r * .58}" fill="none" stroke="${COL[team]}" stroke-width="${r * .24}" stroke-linecap="round" stroke-linejoin="round"/></g>`;
  g.appendChild(grp); return grp;
}
function placeDot(d, x, y, r, work, done) {
  // work: 0..1 progress of the current challenge (or -1); done: seconds since last completion (or big)
  d.setAttribute('transform', `translate(${x},${y})`);
  const ring = d.querySelector('.ring'), arc = d.querySelector('.arc'), chk = d.querySelector('.chk');
  if (work >= 0) { const p = (work * 3) % 1; ring.setAttribute('r', r * (1.2 + .9 * p)); ring.setAttribute('opacity', (1 - p) * .7);
    const R = r * 1.55, a = work * 2 * Math.PI - 1e-4;
    arc.setAttribute('d', `M0,${-R} A${R},${R} 0 ${a > Math.PI ? 1 : 0} 1 ${R * Math.sin(a)},${-R * Math.cos(a)}`); arc.setAttribute('opacity', 1); }
  else { ring.setAttribute('opacity', 0); arc.setAttribute('opacity', 0); }
  const c = clamp(done / .15) * (1 - clamp((done - .9) / .3));
  chk.setAttribute('opacity', done >= 0 ? c : 0); chk.setAttribute('transform', `translate(${r * 2.2},${-r * 1.4 - done * r * .5}) scale(${done >= 0 ? pop(done / .3) : 0})`);
}
function legPos(leg, t) {
  // times alternate arrive/leave for each interior point; first/last points are off-screen entries/exits
  const P = leg.pts, T = leg.times;               // T: [enter0 depart, arrive1, leave1, arrive2, leave2, ..., gone]
  if (t <= T[0]) return { x: P[0][0], y: P[0][1], vis: 0 };
  for (let i = 1; i < P.length; i++) {
    const ta = T[2 * i - 2], tb = T[2 * i - 1];     // travel from P[i-1] (leaving at ta) to P[i] (arriving tb)
    if (t < tb) { const f = inOut((t - ta) / (tb - ta)), hop = Math.sin(Math.PI * clamp((t - ta) / (tb - ta))) * 14;
      return { x: P[i - 1][0] + (P[i][0] - P[i - 1][0]) * f, y: P[i - 1][1] + (P[i][1] - P[i - 1][1]) * f - hop, vis: 1, moving: 1 }; }
    const tl = T[2 * i];
    if (i === P.length - 1) return { x: P[i][0], y: P[i][1], vis: 0 };
    if (tl === undefined || t < tl) return { x: P[i][0], y: P[i][1], vis: 1, at: i, since: t - tb, until: tl };
  }
  return { x: P[P.length - 1][0], y: P[P.length - 1][1], vis: 0 };
}
function runLegs(layer, spec, t) {
  const g = $('.dots', layer); if (!layer._dots) layer._dots = spec.legs.map(l => mkDot(g, l.team, spec.r));
  spec.legs.forEach((leg, k) => {
    const d = layer._dots[k], p = legPos(leg, t);
    let work = -1, done = 99;
    for (const c of leg.done) if (t >= c) done = t - c;
    if (p.at !== undefined) { const c = leg.done[p.at - 1], arrived = t - p.since;   // interior point i ↔ done[i-1]
      if (c !== undefined && t < c) work = clamp((t - arrived) / (c - arrived)); }
    placeDot(d, p.x, p.y, spec.r, work, done < 99 ? done : -1);
    d.style.opacity = p.vis ? 1 : 0;
  });
}
function layerOpacity(el, t, a, b, fin = .5, fout = .45) {
  const o = t < a || t > b ? 0 : Math.min(ease((t - a) / fin), 1 - clamp((t - (b - fout)) / fout));
  el.style.opacity = o; return o;
}
// ---------- conquest simulation (title + 41 neighborhoods) ----------
function sched(route, T0, T1) {
  const n = route.length - 1, per = (T1 - T0) / n;
  return route.map((name, k) => ({ name, a: T0 + k * per, c: T0 + k * per + .3 * per, d: T0 + k * per + .45 * per }));
}
function simState(S, t, routes, skipFirstRed = true, lockTeam = null) {
  const held = {}, last = {}, locks = {};
  for (const team of ['r', 'b']) routes[team].forEach((st, k) => {
    if (team === 'r' && k === 0 && skipFirstRed) return;
    if (t >= st.c && !locks[st.name] && (!last[st.name] || st.c > last[st.name])) { last[st.name] = st.c; held[st.name] = team; }
    if (lockTeam === team && st.lockAt && t >= st.lockAt) locks[st.name] = 1;
  });
  return { held, last, locks };
}
function dotAlong(stops, t) {
  if (t <= stops[0].a) return { x: L.PTS[stops[0].name][0], y: L.PTS[stops[0].name][1], work: -1 };
  for (let k = 0; k < stops.length; k++) {
    const s = stops[k], p = L.PTS[s.name];
    if (t < s.d) return { x: p[0], y: p[1], work: t >= s.a ? clamp((t - s.a) / (s.c - s.a)) : -1, k };
    const nx = stops[k + 1]; if (!nx) return { x: p[0], y: p[1], work: -1, k };
    if (t < nx.a) { const q = L.PTS[nx.name], f = inOut((t - s.d) / (nx.a - s.d)), hop = Math.sin(Math.PI * clamp((t - s.d) / (nx.a - s.d))) * 16;
      return { x: p[0] + (q[0] - p[0]) * f, y: p[1] + (q[1] - p[1]) * f - hop, work: -1, k }; }
  }
}
function paint(svg, held, last, t, locks) {
  if (!svg._p) svg._p = Object.fromEntries([...svg.querySelectorAll('path[data-n]')].map(p => [p.dataset.n, p]));
  for (const [n, p] of Object.entries(svg._p)) {
    const h = held[n]; p.style.fill = h ? COL[h] : '#F1F2EE';
    const age = h ? t - last[n] : 9; p.style.filter = age < .3 ? `brightness(${1.45 - 1.5 * age})` : '';
  }
  const fx = $('.lfx', svg); if (locks) { const key = Object.keys(locks).join('|'); if (fx._k !== key) { fx._k = key;
    fx.innerHTML = Object.keys(locks).map(n => { const [x, y] = L.PTS[n]; return `<circle cx="${x}" cy="${y}" r="17" fill="#1C1E21"/>` + LOCK(x, y, 20); }).join(''); } }
}
function sizeBox(box, r) { box.style.left = r[0] + 'px'; box.style.top = r[1] + 'px'; box.style.width = r[2] + 'px'; box.style.height = r[3] + 'px'; }
const clock = (s) => { s = Math.max(0, Math.round(s)); return `${Math.floor(s / 3600)}:${String(Math.floor(s / 60) % 60).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`; };
function simLayer(t) {
  const S = L.sim, el = $('#L-sim'), o = layerOpacity(el, t, S.start, S.end + .45, .8, .45); if (!o) { $('#L-confetti').style.opacity = 0; return; }
  const box = $('.lbox', el), svg = $('svg', el), f = inOut((t - S.slide) / 1.0);
  sizeBox(box, S.r1.map((v, i) => v + (S.r2[i] - v) * f));
  if (!S._r) S._r = { r: sched(S.route.r, S.T0, S.TZ - .5), b: sched(S.route.b, S.T0, S.TZ - .5) };
  const ts = Math.min(t, S.TZ), st = simState(S, ts, S._r); paint(svg, st.held, st.last, ts);
  const cnt = { r: 0, b: 0 }; Object.values(st.held).forEach(h => cnt[h]++);
  $('.pr', el).textContent = cnt.r; $('.pb', el).textContent = cnt.b;
  $('.pc', el).textContent = clock(6 * 3600 * (1 - clamp((t - S.start) / (S.TZ - S.start))));
  if (!svg._dots) svg._dots = { b: mkDot($('.lfx', svg).parentNode, 'b', 19), r: mkDot($('.lfx', svg).parentNode, 'r', 19) };
  const win = cnt.r === cnt.b ? null : (cnt.r > cnt.b ? 'r' : 'b'), after = t - S.TZ;
  for (const team of ['r', 'b']) {
    const p = dotAlong(S._r[team], ts), d = svg._dots[team];
    let y = p.y; if (after > 0 && team === win) y -= Math.abs(Math.sin(after * 7.5)) * 34;
    placeDot(d, p.x, y, 19, after > 0 ? -1 : p.work, -1);
    d.style.opacity = ease((t - S.start) / .5) * (after > 0 && team !== win ? .45 : 1);
    if (after > 0 && team === win) d.setAttribute('transform', d.getAttribute('transform') + ` scale(${1 + .25 * clamp(after / .3)})`);
  }
  // finale: dim the loser's ground, pop the winner, confetti
  if (after > 0 && win) for (const [n, p] of Object.entries(svg._p)) if (st.held[n] && st.held[n] !== win) p.style.opacity = 1 - .55 * clamp(after / .5); else p.style.opacity = 1;
  const W = $('.winner', el); W.textContent = win ? (win === 'r' ? 'The red team wins!' : 'The blue team wins!') : ''; W.style.background = win ? COL[win] : 'transparent';
  W.style.transform = `translateX(-50%) scale(${after > 0 ? pop(after / .45) : 0})`;
  $('.pill', el).style.transform = `translateX(-50%) scale(${1 + .12 * Math.sin(Math.PI * clamp(after / .4))})`;
  const cf = $('#L-confetti'); cf.style.opacity = after > 0 && t < S.end + .3 ? 1 : 0;
  if (after > 0) [...cf.children].forEach((c, i) => { const r1 = (i * 7919 % 1000) / 1000, r2 = (i * 104729 % 1000) / 1000, r3 = (i * 1299709 % 1000) / 1000;
    const dt = after - r1 * .5; if (dt < 0) { c.style.opacity = 0; return; }
    const x = 80 + r2 * 1760 + Math.sin(dt * (2 + 3 * r3) + i) * 40, y = -60 - r3 * 300 + dt * (260 + 240 * r1) + 180 * dt * dt;
    c.style.opacity = 1; c.style.transform = `translate(${x}px,${y}px) rotate(${dt * (300 + 500 * r2) + i * 37}deg) scaleX(${Math.cos(dt * (6 + 5 * r3))})`; });
}
// ---------- handheld Coit Tower photo, then upload in the app ----------
function tapAt(fx, x, y, age) { const q = clamp(age / .45); fx.style.left = x + 'px'; fx.style.top = y + 'px';
  fx.style.opacity = age >= 0 && age < .45 ? (1 - q) * .9 : 0; fx.style.transform = `scale(${.5 + q * 1.4})`; }
function phoneLayer(t) {
  const P = L.phone, el = $('#L-phone'), o = layerOpacity(el, t, P.start, P.end + .45, .5, .45); if (!o) return;
  const lt = t - P.start, ph = $('.ph', el), up = ease(lt / .7);
  const sx = Math.sin(lt * .9) * 10 + Math.sin(lt * 2.3) * 3, sy = Math.sin(lt * 1.4) * 7, rot = Math.sin(lt * 1.1) * 2.2 + Math.sin(lt * 2.9) * .6;
  const calm = clamp((t - P.app) / .8);                        // hold steadier while using the app
  ph.style.transform = `translate(${sx * (1 - .6 * calm)}px, ${sy * (1 - .6 * calm) + (1 - up) * 500}px) rotate(${rot * (1 - .7 * calm)}deg)`;
  // camera
  const frozen = t >= P.shutter, tt = frozen ? P.shutter - P.start : lt, snap = t - P.shutter;
  const lx = -(Math.sin(tt * .9) * 10 + Math.sin(tt * 2.3) * 3) * 1.8 + Math.sin(tt * .5) * 6, ly = -(Math.sin(tt * 1.4) * 7) * 1.8;
  $('.vf-live', el).style.transform = `translate(${lx}px, ${ly}px) rotate(${-(Math.sin(tt * 1.1) * 2.2) * 1.2}deg)`;
  $('.vf-flash', el).style.opacity = snap > 0 ? 1 - clamp(snap / .35) : 0;
  $('.vf-btn', el).style.transform = `scale(${1 - .16 * Math.sin(Math.PI * clamp((t - P.shutter + .12) / .24))})`;
  const roll = $('.cam-roll-img', el); roll.style.opacity = snap > .25 ? 1 : 0;
  $('.cam-roll', el).style.transform = `scale(${snap > .25 ? 1 + .25 * Math.sin(Math.PI * clamp((snap - .25) / .3)) : 1})`;
  const vf = $('.vf', el); vf.style.transform = snap > 0 && snap < .6 ? `scale(${1 - .05 * Math.sin(Math.PI * clamp(snap / .5))})` : '';
  // app
  const app = $('.app', el), ai = ease((t - P.app) / .35); app.style.opacity = ai; $('.cam', el).style.opacity = 1 - ai;
  const fx = $('.tapfx', el);
  const sheet = $('.sheet', el), sUp = inOut((t - P.sheetUp) / .4), sDn = inOut((t - P.sheetDown) / .35);
  sheet.style.transform = `translateY(${110 - 110 * sUp + 110 * sDn}%)`;
  $('.pick-chk', el).style.opacity = t >= P.pick ? 1 : 0; $('.th.pick', el).style.outlineWidth = t >= P.pick ? '5px' : '0';
  const inSlot = t >= P.upStart; $('.slot-img', el).style.opacity = inSlot ? ease((t - P.upStart) / .25) : 0;
  $('.slot-empty', el).style.opacity = inSlot ? 0 : 1; $('.slot', el).style.borderStyle = inSlot ? 'solid' : 'dashed';
  const upEl = $('.up', el), prog = clamp((t - P.upStart) / (P.upEnd - P.upStart));
  upEl.style.opacity = inSlot ? 1 - clamp((t - P.upEnd - .6) / .3) : 0; $('.up-bar i', el).style.width = (prog * 100) + '%';
  $('.up-txt', el).textContent = prog >= 1 ? 'Uploaded ✓' : 'Uploading…';
  const cb = $('.ph-btn', el), tap = t - P.tap;
  if (tap > .12) { cb.textContent = '✓ Completed · 11:58'; cb.style.background = '#C42847'; cb.style.color = '#fff'; }
  else if (prog >= 1) { cb.textContent = 'Complete'; cb.style.background = '#C42847'; cb.style.color = '#fff'; }
  else { cb.textContent = 'Complete'; cb.style.background = '#E8EAEC'; cb.style.color = '#9AA1AB'; }
  cb.style.transform = `scale(${1 - .05 * Math.sin(Math.PI * clamp((tap + .05) / .25))})`;
  // finger taps: add photo (slot), the Coit thumbnail, then Complete
  if (t < P.pick - .05) tapAt(fx, 199, 340, t - P.addTap);
  else if (t < P.tap - .05) tapAt(fx, 76, 452, t - P.pick);
  else tapAt(fx, 199, 552, t - P.tap);
}
// ---------- North Beach & Hayes dots ----------
function zoomLayer(id, spec, t) { const el = $(id); if (!layerOpacity(el, t, spec.start, spec.end, .3, .3)) return; runLegs(el, spec, t); }
function tieResolve(t) {
  const p = document.querySelector('[data-id="6a-tiebreak"] path[data-n="North Beach"]'), r = L.nb.resolve;
  if (!p) return; const age = t - r;
  p.style.fill = age >= 0 ? '#C42847' : ''; p.style.filter = age >= 0 && age < .35 ? `brightness(${1.5 - 1.4 * age})` : '';
}
function hayesExtras(t) {
  const H = L.hay, p = document.querySelector('[data-id="6b-sweep"] path[data-n="Hayes Valley"]');
  if (p) p.style.fill = t < H.fill ? '#F1F2EE' : '';
}
// ---------- strategy race ----------
function stratLayer(t) {
  const S = L.strat, el = $('#L-strat'); if (!layerOpacity(el, t, S.start, S.end, .45, .45)) return;
  const svg = $('svg', el), end = S.end - .6;
  if (!S._r) {
    const red = S.red.map((name, k) => ({ name, a: S.T0 + k * .8, c: S.T0 + k * .8 + .3, d: S.T0 + k * .8 + .38 }));
    const blue = S.blue.map((name, k) => { const a = S.T0 + k * 3.1; return { name, a, c: a + .7, c2: a + 1.4, c3: a + 2.1, lockAt: a + 2.2, d: a + 2.45 }; });
    S._r = { r: red, b: blue };
  }
  const st = simState(S, t, S._r, false, 'b'); paint(svg, st.held, st.last, t, st.locks);
  const cnt = { r: 0, b: 0 }; Object.values(st.held).forEach(h => cnt[h]++);
  $('.pr', el).textContent = cnt.r; $('.pb', el).textContent = cnt.b;
  $('.pc', el).textContent = clock(3 * 3600 + 600 - (t - S.start) * 190);
  if (!svg._dots) svg._dots = { b: mkDot($('.lfx', svg).parentNode, 'b', 19), r: mkDot($('.lfx', svg).parentNode, 'r', 19) };
  for (const team of ['r', 'b']) {
    const stops = S._r[team], p = dotAlong(stops, t); let done = -1;
    for (const s of stops) for (const c of [s.c, s.c2, s.c3]) if (c && t >= c && t - c < 1.2) done = t - c;
    let work = -1; if (p.work >= 0 && team === 'b') { const s = stops[p.k]; work = clamp((t - s.a) / (s.c3 - s.a)); } else work = p.work;
    placeDot(svg._dots[team], p.x, p.y, 19, work, done); svg._dots[team].style.opacity = ease((t - S.start) / .5);
  }
}
function renderLayers(t) { simLayer(t); phoneLayer(t); zoomLayer('#L-nb', L.nb, t); zoomLayer('#L-hay', L.hay, t); hayesExtras(t); tieResolve(t); stratLayer(t); }
'''
