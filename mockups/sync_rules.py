#!/usr/bin/env python3
"""rules.json is the single source of truth for the game rules. This script rewrites the
rules block (between <!-- rules:start --> and <!-- rules:end -->) in guide.html; the game
app links to the guide instead of repeating the rules. build_brochure.py reads rules.json directly. Run after editing rules.json:
    python3 mockups/sync_rules.py && python3 mockups/build_brochure.py
"""
import json, os, re, html
os.chdir(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open('rules.json'))

def items(indent):
    return '\n'.join(f'{indent}<li><b>{html.escape(b)}</b>{(" " + html.escape(t)) if t else ""}</li>'
                     for b, t in R['rules'])

def intro(cls):
    c = f' class="{cls}"' if cls else ''
    return '\n'.join(f'<p{c}>{html.escape(p)}</p>' for p in R['intro'])

def enc():
    b, t = R['encouraged']
    return f'<b>{html.escape(b)}</b> {html.escape(t)}'

BLOCKS = {
    'guide.html': lambda: f'    {intro("intro")}\n    <ul class="rules">\n{items("      ")}\n    </ul>\n    <p class="intro">{enc()}</p>',
}
for fn, block in BLOCKS.items():
    s = open(fn).read()
    new, n = re.subn(r'(<!-- rules:start -->\n).*?( *<!-- rules:end -->)',
                     lambda m: m.group(1) + block() + '\n' + m.group(2), s, flags=re.S)
    assert n == 1, fn
    open(fn, 'w').write(new)
    print(fn, 'rules synced:', len(R['rules']))
