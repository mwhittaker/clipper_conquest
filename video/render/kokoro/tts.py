"""Kokoro voiceover, one sentence at a time so captions get exact timings.
Reads /vo/lines.json [{id, text}], writes /vo/<id>.wav and /vo/captions.json
{id: [[start_s, end_s, sentence], ...]} (times relative to the start of the clip)."""
import json, re, sys
import numpy as np, soundfile as sf
from kokoro import KPipeline
voice = sys.argv[1] if len(sys.argv) > 1 else 'af_heart'
ONLY = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None   # regenerate just these ids
SR, GAP, SPEED = 24000, 0.16, 1.12
pipe = KPipeline(lang_code=voice[0], repo_id='hexgrad/Kokoro-82M')
import os
caps = json.load(open('/vo/captions.json')) if ONLY and os.path.exists('/vo/captions.json') else {}
SAY = {'11:58': 'eleven fifty-eight', '12:30': 'twelve thirty', 'Pier 39': 'Pier thirty-nine', ' 41 ': ' forty-one '}
for L in json.load(open('/vo/lines.json')):
    if ONLY and L['id'] not in ONLY: continue
    sents = [s.strip() for s in re.split(r'(?<=[.?!])\s+', L['text']) if s.strip()]
    chunks, t, cl = [], 0.0, []
    for s in sents:
        say = s
        for k, v in SAY.items(): say = say.replace(k, v)
        a = np.concatenate([x for _, _, x in pipe(say, voice=voice, speed=SPEED)])
        loud = np.where(np.abs(a) > 0.01)[0]                     # trim leading/trailing silence
        if len(loud): a = a[max(0, loud[0] - int(.04 * SR)): loud[-1] + int(.06 * SR)]
        cl.append([round(t, 3), round(t + len(a) / SR, 3), s])
        chunks += [a, np.zeros(int(GAP * SR), dtype=a.dtype)]
        t += len(a) / SR + GAP
    sf.write(f'/vo/{L["id"]}.wav', np.concatenate(chunks[:-1]), SR)
    caps[L['id']] = cl
    print('ok', L['id'], round(t - GAP, 2), flush=True)
json.dump(caps, open('/vo/captions.json', 'w'), indent=1)
