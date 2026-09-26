#!/usr/bin/env python3
"""Write mockups/challenges.json — the recommended trio of every neighborhood, keyed by
the official Analysis Neighborhood name, for guide.html (and later the game app).
Run from anywhere: python3 challenges/build_guide_data.py
"""
import re, json, os
from hoodparse import all_hoods, md_inline as md
os.chdir(os.path.dirname(os.path.abspath(__file__)))

order = json.load(open('../mockups/hood_order.json'))
name_by_clean = {re.sub(r'\s*\(.*\)', '', o): o for o in order}

def fail_kind(f):
    f = f.lower()
    return 'one-shot' if 'one-shot' in f or 'one shot' in f else ('retryable' if f.startswith('retry') else '')

out = {}
for h in all_hoods():
    out[name_by_clean[h['clean']]] = [
        # published: type, time estimate and cost stay private (organizer-only, in challenges/*.md)
        dict({'title': md(c['title']), 'do': md(c['do']), 'where': md(c['where']),
              'fail': fail_kind(c['fail']), 'photo': md(c['photo'])},
             **({'img': 'img/' + c['img'], 'credit': md(c['img_credit'])} if c['img'] else {}))
        for c in h['trio_cands']]
for c in (c for v in out.values() for c in v if 'img' in c):
    assert os.path.exists('../mockups/' + c['img']), 'missing image: mockups/' + c['img']

assert len(out) == 41, len(out)
json.dump(out, open('../mockups/challenges.json', 'w'), ensure_ascii=False, indent=0)
print('mockups/challenges.json:', len(out), 'hoods,', sum(len(v) for v in out.values()), 'challenges')
