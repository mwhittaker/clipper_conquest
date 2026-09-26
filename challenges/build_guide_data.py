#!/usr/bin/env python3
"""Write mockups/challenges.json — the recommended trio of every neighborhood, keyed by
the official Analysis Neighborhood name, for guide.html (and later the game app).
Run from anywhere: python3 challenges/build_guide_data.py
"""
import re, glob, html, json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

order = json.load(open('../mockups/hood_order.json'))
name_by_clean = {re.sub(r'\s*\(.*\)', '', o): o for o in order}

def field(block, label):
    m = re.search(r'- \*\*' + label + r':\*\*\s*(.*?)(?=\n- \*\*|\Z)', block, re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''

def md(s):
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'<i>\1</i>', s)
    return s

out = {}
for fn in glob.glob('*.md'):
    if fn in ('BRIEF.md', 'QUEUE.md', 'DIGEST.md', 'JETLAG_EXAMPLES.md'): continue
    text = open(fn).read()
    clean = re.sub(r'\s*\(.*\)', '', re.match(r'# (.+)', text).group(1).strip())
    official = name_by_clean[clean]
    cands = []
    for m in re.finditer(r'### (\d+)\.\s*(.+?)\n(.*?)(?=### \d+\.|## Recommended trio)', text, re.S):
        b = m.group(3)
        tc = field(b, 'Time'); tm = re.match(r'(.*?)\|\s*\*\*Cost:\*\*\s*(.*)', tc)
        fail = field(b, 'Failable').lower()
        cands.append({
            'title': md(m.group(2).strip()), 'do': md(field(b, 'Do')), 'where': md(field(b, 'Where')),
            'time': (tm.group(1) if tm else tc).strip(), 'cost': (tm.group(2) if tm else '').strip(),
            'fail': 'one-shot' if 'one-shot' in fail or 'one shot' in fail else ('retryable' if fail.startswith('retry') else ''),
            'type': field(b, 'Type'), 'photo': md(field(b, 'Photo')),
        })
    trio = [int(x) for x in re.findall(r'\d+', re.search(r'## Recommended trio\s*\n+\**([\d,\sand&]+)', text).group(1))][:3]
    out[official] = [cands[n - 1] for n in trio]

assert len(out) == 41, len(out)
json.dump(out, open('../mockups/challenges.json', 'w'), ensure_ascii=False, indent=0)
print('mockups/challenges.json:', len(out), 'hoods,', sum(len(v) for v in out.values()), 'challenges')
