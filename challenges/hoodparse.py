"""Shared parser for the per-neighborhood challenge files (challenges/*.md).

Every builder (guide data, review artifact, brochure) reads the files through here, so the
format is defined once. Trio numbers are resolved by the `### N.` heading number, never by
position, so deleting a candidate without renumbering can't pick the wrong challenge.
"""
import glob, html, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
NOT_HOODS = {'BRIEF.md', 'JETLAG_EXAMPLES.md'}


def hood_files():
    return sorted(f for f in glob.glob(os.path.join(HERE, '*.md')) if os.path.basename(f) not in NOT_HOODS)


def field(block, label):
    m = re.search(r'- \*\*' + label + r':\*\*\s*(.*?)(?=\n- \*\*|\Z)', block, re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''


def md_inline(s):
    """Escape, then render **bold** and *italic*."""
    s = html.escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'<i>\1</i>', s)
    return s


def plain(s):
    """Strip markdown emphasis markers for plain-text contexts (e.g. the brochure legend)."""
    return re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', s).strip()


def parse(fn):
    text = open(fn).read()
    name = re.match(r'# (.+)', text).group(1).strip()
    sketch_m = re.search(r'^# .+\n+(.+?)\n\n## Candidates', text, re.S)
    cands = []
    for m in re.finditer(r'### (\d+)\.\s*(.+?)\n(.*?)(?=### \d+\.|## Recommended trio)', text, re.S):
        b = m.group(3)
        tc = field(b, 'Time'); tm = re.match(r'(.*?)\|\s*\*\*Cost:\*\*\s*(.*)', tc)
        cands.append({
            'num': int(m.group(1)), 'title': m.group(2).strip(),
            'do': field(b, 'Do'), 'where': field(b, 'Where'),
            'time': (tm.group(1) if tm else tc).strip(), 'cost': (tm.group(2) if tm else '').strip(),
            'fail': field(b, 'Failable'), 'type': field(b, 'Type'), 'photo': field(b, 'Photo'),
        })
    trio_m = re.search(r'## Recommended trio\s*\n+\**([\d,\sand&]+)\**(.*)', text, re.S)
    trio = [int(x) for x in re.findall(r'\d+', trio_m.group(1))][:3]
    by_num = {c['num']: c for c in cands}
    missing = [n for n in trio if n not in by_num]
    assert not missing, f'{os.path.basename(fn)}: trio names candidate(s) {missing} that do not exist'
    return {
        'file': fn, 'name': name, 'clean': re.sub(r'\s*\(.*\)', '', name),
        'sketch': re.sub(r'\s+', ' ', sketch_m.group(1)) if sketch_m else '',
        'cands': cands, 'trio': trio, 'trio_cands': [by_num[n] for n in trio],
        'note': re.sub(r'\s+', ' ', trio_m.group(2)).strip(' —-*'),
    }


def all_hoods():
    return [parse(f) for f in hood_files()]
