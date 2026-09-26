#!/usr/bin/env python3
"""Rebuild docs/ — the GitHub Pages copy of the study guide — from the sources.

    python3 docs_build.py https://USERNAME.github.io/clipper_conquest/

Steps:
  1. challenges/build_guide_data.py  -> mockups/challenges.json   (challenge edits)
  2. mockups/sync_rules.py           -> rules block in guide.html  (rules.json edits)
  3. mockups/build_brochure.py       -> mockups/brochure.html      (local build, unchanged)
  4. QR code for BASE_URL            -> mockups/qr_codes.public.json
     (same structure as qr_codes.json, plus "guide_url"; regenerated only when the URL
     changes; uses the `qrcode` lib if installed, else a python:3.12-slim container)
  5. mockups/build_brochure.py --qr qr_codes.public.json --out docs/brochure.html
  6. copy guide.html -> docs/index.html plus the data files it fetches; write .nojekyll
  7. check the published files for local-only URLs and missing relative references

mockups/qr_codes.json is never touched, so the local build keeps working.
docs/ is wiped on each run except for a CNAME file, if you add one for a custom domain.
"""
import argparse, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MOCK = os.path.join(ROOT, 'mockups')
DOCS = os.path.join(ROOT, 'docs')
PUBLIC_QR = os.path.join(MOCK, 'qr_codes.public.json')
DATA_FILES = ['sf_neighborhoods.geojson', 'muni_routes.geojson', 'challenges.json',
              'clipper-conquest-rules.mp4', 'clipper-conquest-rules.jpg']   # rules video + poster
KEEP = {'CNAME'}
# Must match how mockups/qr_codes.json was made (verified byte-identical): qrcode defaults
# (error correction M), box_size=8, border=2.
QR_SCRIPT = r'''
import base64, io, sys, qrcode
q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
q.add_data(sys.argv[1]); q.make(fit=True)
b = io.BytesIO(); q.make_image().save(b, format='PNG')
print('data:image/png;base64,' + base64.b64encode(b.getvalue()).decode())
'''
BAD_URL = re.compile(r'//[a-z0-9-]+\.local\b|localhost|127\.0\.0\.1|:8013\b|file://')


def run(*cmd):
    shown = ['python3'] + [os.path.relpath(c, ROOT) if os.path.isabs(c) else c for c in cmd[1:]]
    print('+', ' '.join(shown), flush=True)
    subprocess.run(cmd, check=True)


def qr_data_uri(url):
    try:
        import qrcode  # noqa: F401
        out = subprocess.run([sys.executable, '-c', QR_SCRIPT, url],
                             check=True, capture_output=True, text=True).stdout
    except ImportError:
        print('  (no qrcode lib on host; generating in a python:3.12-slim container)')
        out = subprocess.run(
            ['docker', 'run', '--rm', 'python:3.12-slim', 'sh', '-c',
             'pip install -q --root-user-action=ignore "qrcode[pil]" >/dev/null 2>&1 && python -c "$0" "$1"',
             QR_SCRIPT, url],
            check=True, capture_output=True, text=True).stdout
    uri = out.strip().splitlines()[-1]
    assert uri.startswith('data:image/png;base64,'), out
    return uri


def public_qr(base_url):
    try:
        cached = json.load(open(PUBLIC_QR))
        if cached.get('guide_url') == base_url:
            print('QR: reusing', os.path.relpath(PUBLIC_QR, ROOT), 'for', base_url)
            return
    except (OSError, ValueError):
        pass
    print('QR: generating for', base_url)
    json.dump({'guide': qr_data_uri(base_url), 'guide_url': base_url}, open(PUBLIC_QR, 'w'), indent=1)


def check(files):
    ok = True
    for fn in files:
        if not fn.endswith('.html'):
            continue
        text = open(os.path.join(DOCS, fn)).read()
        for m in BAD_URL.finditer(text):
            print(f'ERROR {fn}: local-only URL near {text[max(0, m.start() - 40):m.end() + 40]!r}')
            ok = False
        refs = re.findall(r'''(?:fetch\(|\.src\s*=\s*|(?:src|href)=)\s*['"]([^'"#?]+)''', text)
        for ref in refs:
            if re.match(r'[a-z]+:', ref):   # data:, https:, mailto: ...
                continue
            if not os.path.exists(os.path.join(DOCS, ref)):
                print(f'ERROR {fn}: references {ref!r}, which is not in docs/')
                ok = False
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('base_url', help='public URL of docs/, e.g. https://USERNAME.github.io/clipper_conquest/')
    base_url = ap.parse_args().base_url
    if not re.match(r'https?://[^/]+', base_url):
        ap.error('base_url must be an absolute http(s) URL')
    if not base_url.endswith('/'):
        base_url += '/'

    run(sys.executable, os.path.join(ROOT, 'challenges', 'build_guide_data.py'))
    run(sys.executable, os.path.join(MOCK, 'sync_rules.py'))
    run(sys.executable, os.path.join(MOCK, 'build_brochure.py'))
    public_qr(base_url)

    os.makedirs(DOCS, exist_ok=True)
    for fn in os.listdir(DOCS):
        if fn in KEEP:
            continue
        p = os.path.join(DOCS, fn)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    run(sys.executable, os.path.join(MOCK, 'build_brochure.py'),
        '--qr', PUBLIC_QR, '--out', os.path.join(DOCS, 'brochure.html'))
    shutil.copyfile(os.path.join(MOCK, 'guide.html'), os.path.join(DOCS, 'index.html'))
    for fn in DATA_FILES:
        shutil.copyfile(os.path.join(MOCK, fn), os.path.join(DOCS, fn))
    open(os.path.join(DOCS, '.nojekyll'), 'w').close()

    files = sorted(os.listdir(DOCS))
    if not check(files):
        sys.exit('docs/ failed checks (see above)')
    print('\ndocs/ ready for', base_url)
    for fn in files:
        print(f'  {fn:28s} {os.path.getsize(os.path.join(DOCS, fn)) // 1024:5d} KB')


if __name__ == '__main__':
    main()
