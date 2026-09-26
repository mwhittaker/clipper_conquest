#!/usr/bin/env python3
"""Build the storyboard review page (video/motifs.html — kept at that path so the
artifact URL stays stable): one row per beat with its frame, timing, voiceover and the
motion note, plus the voice samples. Frames come from video/frames/build.py.
"""
import base64, io, os, html
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
TTS = os.path.join(HERE, 'render', 'voice-samples')   # optional Piper/Kokoro samples for the review page

# (frame, section, time, voiceover, what moves)
BEATS = [
 ('0-tap', '1 · Cold open', '0:00', '', 'A card reader on a white screen. A big Clipper Conquest card swipes in, taps (beep, the reader lights green), then swipes out, wiping the screen white behind it.'),
 ('1b-title', '1 · Cold open', '0:08', 'Two teams. Forty-one neighborhoods. One clock. This is Clipper Conquest.', 'A few neighborhoods fill red and blue; the title slides in.'),
 ('2a-grey', '2 · The basic idea', '0:14', 'Clipper Conquest is played by two teams, the red team and the blue team, that race to conquer as many San Francisco neighborhoods as possible. Whichever team has more neighborhoods when the clock hits zero is the winner.', 'Map resets to grey; the 41 counts up as neighborhoods ripple.'),
 ('2b-challenges', '2 · The basic idea', '0:26', "Every one of the city's 41 neighborhoods has three unique challenges. For example, one challenge might ask you to get three antique arcade machines running at the same time. Another might ask two teammates to count the sea lions at Pier 39 and agree on the number. Whichever team has completed more of a neighborhood's challenges holds it.", 'Zoom to North Beach, which turns yellow; three challenge cards slide in one by one.'),
 ('3a-muni', '3 · Muni only', '0:42', 'You get around on Muni, and only Muni: buses, Metro, streetcars and cable cars. No BART, no Caltrain, no cars and no bikes. And no running unless a challenge says to. You can only speedwalk.', 'Pull back; Muni lines draw in their real colors. The red team dot rides the F-line and the Powell-Mason cable car to North Beach. Checklist ticks in.'),
 ('4a-phone', '4 · Photo proof', '0:55', 'When you finish a challenge, take a photo. Every completion needs one.', 'Phone slides up on Get to Coit Tower; camera shutter click.'),
 ('4b-upload', '4 · Photo proof', '1:00', 'Then upload it in the app and tap Complete. The moment you log it is the moment it counts.', 'A Coit Tower photo drops in; thumb taps Complete; it becomes a check with the time, 11:58.'),
 ('5a-empty', '5 · Conquering', '1:05', "Here's how that plays out in North Beach.", 'Back on North Beach, empty timeline.'),
 ('5b-blue', '5 · Conquering', '1:09', "The blue team completes one. North Beach is the blue team's.", 'Row slides into the timeline; North Beach floods blue; badge 0-1.'),
 ('5c-tied1', '5 · Conquering', '1:13', "But be careful. The other team can steal a neighborhood by completing more of its challenges than you. The red team completes one. Now it's one each, but the blue team got there first, so North Beach stays blue.", 'Red row; badge ticks to 1-1; North Beach stays blue (the blue team got there first).'),
 ('5d-flip', '5 · Conquering', '1:21', 'And then another. Two beats one. The red team steals North Beach.', 'Third row; North Beach flips red; highlight row "The red team steals North Beach".'),
 ('5e-tie2', '5 · Conquering', '1:26', "The blue team answers with a second. Now it's two each. So who holds it?", 'Fourth row; North Beach fills with red and blue stripes and freezes.'),
 ('6a-tiebreak', '6 · Ties and locks', '1:31', 'Ties go to whichever team reached that count first. The red team logged its second at 11:58. The blue team logged its second at 12:30. So the red team keeps North Beach.', 'Timeline slides in; a marker sweeps left to right; flag pops at 11:58.'),
 ('6b-sweep', '6 · Ties and locks', '1:42', 'Complete all three and the neighborhood is locked. No one can steal it.', 'Cut to Hayes Valley: three checks, spaced out to feel slow; then the lock snaps shut with a clunk.'),
 ('7a-costs', '7 · Quick or locked', '1:51', "So there's a choice. One challenge grabs a neighborhood fast, but it can be stolen. All three lock it, but that takes time. Here, the red team zips around grabbing neighborhoods, while the blue team locks down a few.", "Fresh map; the red dot zips around claiming neighborhoods with one challenge each, while the blue dot slowly locks a few."),
 ('8a-end', '8 · Close', '2:02', 'Whichever team has more neighborhoods when the clock hits zero wins. Every rule and every challenge is in the guide.', 'Map fades; end card with the guide QR code.'),
]
VOICES = [('en_US-lessac-high', 'Lessac — neutral, clear'), ('en_US-ryan-high', 'Ryan — warmer, male'), ('en_US-amy-medium', 'Amy — brighter, female')]

def img(f):
    im = Image.open(os.path.join(HERE, 'frames', f + '.png')).convert('RGB').resize((1280, 720), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=78, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
def aud(v):
    p = os.path.join(TTS, v + '.mp3')
    return 'data:audio/mpeg;base64,' + base64.b64encode(open(p, 'rb').read()).decode() if os.path.exists(p) else ''

rows, last = [], None
for f, sec, t, vo, note in BEATS:
    if sec != last:
        rows.append(f'<h2 class="sec">{html.escape(sec)}</h2>'); last = sec
    rows.append(f'''<article class="beat">
  <figure><img src="{img(f)}" alt="Frame {f}" loading="lazy"></figure>
  <div class="txt"><p class="tc">{t}</p>
    {f'<p class="vo">“{html.escape(vo)}”</p>' if vo else '<p class="vo mute">(no voiceover)</p>'}
    <p class="note">{html.escape(note)}</p></div>
</article>''')

voices = ''.join(f'<figure class="voice"><figcaption>{c}</figcaption><audio controls preload="none" src="{aud(v)}"></audio></figure>' for v, c in VOICES if aud(v))

page = f'''<title>Rules Video Storyboard</title>
<style>
:root {{ --bg:#fff; --ink:#1C1E21; --muted:#6A7076; --line:#D9DDE1; --card:#F6F7F8; --red:#C42847; --blue:#1D6FB8; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ color-scheme:dark; --bg:#141619; --ink:#ECEEF1; --muted:#9AA1AB; --line:#2B2F36; --card:#1C1F24; --red:#E0526F; --blue:#5D9FD6; }} }}
:root[data-theme="dark"] {{ color-scheme:dark; --bg:#141619; --ink:#ECEEF1; --muted:#9AA1AB; --line:#2B2F36; --card:#1C1F24; --red:#E0526F; --blue:#5D9FD6; }}
body {{ background:var(--bg); color:var(--ink); font-family:system-ui,-apple-system,sans-serif; line-height:1.5; padding-inline:16px; padding-block:24px 64px; }}
main {{ max-width:1080px; margin:0 auto; }}
h1 {{ font-size:clamp(30px,6vw,46px); line-height:1.05; margin:0 0 8px; letter-spacing:-.02em; }}
h1 b {{ color:var(--blue); }} h1 i {{ color:var(--red); font-style:normal; }}
.intro {{ color:var(--muted); max-width:66ch; margin:0 0 6px; }}
.sec {{ font-size:15px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin:36px 0 10px; padding-top:12px; border-top:2px solid var(--ink); }}
.beat {{ display:grid; grid-template-columns:minmax(0,1.5fr) minmax(0,1fr); gap:20px; align-items:start; margin-bottom:18px; }}
.beat figure {{ margin:0; }} .beat img {{ width:100%; height:auto; display:block; border-radius:10px; border:1px solid var(--line); }}
.tc {{ font-variant-numeric:tabular-nums; font-weight:700; color:var(--muted); margin:0 0 4px; font-size:14px; }}
.vo {{ font-size:17px; margin:0 0 8px; }} .vo.mute {{ color:var(--muted); font-style:italic; }}
.note {{ font-size:14px; color:var(--muted); margin:0; padding-left:10px; border-left:3px solid var(--line); }}
.voices {{ margin-top:40px; padding-top:12px; border-top:2px solid var(--ink); }}
.voice {{ margin:0 0 14px; }} .voice figcaption {{ font-size:15px; margin-bottom:4px; }} .voice audio {{ width:100%; max-width:520px; }}
@media (max-width: 760px) {{ .beat {{ grid-template-columns:minmax(0,1fr); gap:8px; }} }}
</style>
<main>
<h1><b>Rules video</b> <i>storyboard</i></h1>
<p class="intro">Every beat of the video in order, in the guide and app look: the frame, when it lands, the voiceover line, and what moves. About 2:10 total. Sections 1–8 match <code>video/SCRIPT.md</code>.</p>
{''.join(rows)}
<section class="voices"><h2 class="sec" style="border:0; margin-top:0">Voice samples (Piper, local)</h2>{voices}</section>
</main>'''
open(os.path.join(HERE, 'motifs.html'), 'w').write(page)
print('storyboard:', len(BEATS), 'beats,', len(page) // 1024, 'KB')
