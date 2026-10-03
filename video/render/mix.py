#!/usr/bin/env python3
"""Build the ffmpeg command that mixes each beat's voiceover at its timeline offset plus a
few synthesized sound effects, then muxes with the rendered frames into the final MP4
(out/clipper-conquest-rules.mp4; copy it to rules-video.mp4 at the repo top level).
Prints the shell command; run it inside an ffmpeg container with /work = video/render.
See video/README.md.
"""
import json, os, shlex
HERE = os.path.dirname(os.path.abspath(__file__))
tl = json.load(open(os.path.join(HERE, 'timeline.json')))

# input 0 is the frames; each audio input n is resampled, delayed to its time and labeled
inputs, filters, labels = ['-framerate', str(tl['fps']), '-i', '/work/out/frames/f%05d.jpg'], [], []
n = 1
for b in tl['beats']:
    if b['vo'] is None: continue
    inputs += ['-i', f'/work/vo/{b["id"]}.wav']
    ms = int(b['vo'] * 1000)
    filters.append(f'[{n}:a]aresample=48000,aformat=channel_layouts=mono,adelay={ms}|{ms},volume=1.0[v{n}]')
    labels.append(f'[v{n}]'); n += 1

# synthesized sound effects: (time in s, lavfi source, volume); the event times come from
# layers.py via timeline.json
SFX = [
    (0.30, 'anoisesrc=d=0.7:c=pink:a=0.5,bandpass=f=1400:w=1800,afade=t=in:d=0.35,afade=t=out:st=0.35:d=0.35', 0.55),   # whoosh in
    (1.20, 'sine=f=1568:d=0.09', 0.32),                                              # tap chime, two notes
    (1.29, 'sine=f=2093:d=0.16', 0.30),
    (1.22, "aevalsrc='0.25*sin(2*PI*(2600+2600*t)*t)*exp(-5*t)':d=0.7", 0.35),       # sparkle shimmer
    (2.30, 'anoisesrc=d=0.8:c=pink:a=0.5,bandpass=f=1100:w=1600,afade=t=in:d=0.25,afade=t=out:st=0.3:d=0.5', 0.6),     # whoosh out
    (tl['events']['shutter'], 'anoisesrc=d=0.06:c=white:a=0.7,afade=t=out:st=0.02:d=0.04', 0.4),   # shutter click-clack
    (tl['events']['shutter'] + 0.09, 'anoisesrc=d=0.05:c=white:a=0.5,afade=t=out:st=0.01:d=0.04', 0.3),
    (tl['events']['tap'], 'sine=f=900:d=0.05,afade=t=out:st=0.01:d=0.04', 0.25),                   # soft tap
    (tl['events']['win'], "aevalsrc='0.22*(sin(2*PI*784*t)+sin(2*PI*988*t)*gte(t,0.12)+sin(2*PI*1175*t)*gte(t,0.24)+sin(2*PI*1568*t)*gte(t,0.36))*exp(-2.2*t)':d=1.6", 0.5),  # win fanfare
    (tl['events']['win'] + 0.05, "anoisesrc=d=1.2:c=pink:a=0.25,highpass=f=3000,afade=t=out:st=0.1:d=1.1", 0.35),  # confetti rustle
    (tl['events']['lock'], 'sine=f=110:d=0.18', 0.9),                             # lock clunk
    (tl['events']['lock'] + 0.02, 'anoisesrc=d=0.05:c=brown:a=0.8', 0.5),
]
for t, src, vol in SFX:
    inputs += ['-f', 'lavfi', '-i', src]
    ms = int(t * 1000)
    filters.append(f'[{n}:a]aresample=48000,aformat=channel_layouts=mono,volume={vol},adelay={ms}|{ms}[s{n}]')
    labels.append(f'[s{n}]'); n += 1

filters.append(f'{"".join(labels)}amix=inputs={len(labels)}:normalize=0:dropout_transition=0,apad,atrim=0:{tl["total"]},loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]')
cmd = (['ffmpeg', '-y', '-loglevel', 'error'] + inputs +
       ['-filter_complex', ';'.join(filters), '-map', '0:v', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(tl['fps']),
        '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-t', str(tl['total']), '/work/out/clipper-conquest-rules.mp4'])
print(' '.join(shlex.quote(c) for c in cmd))
