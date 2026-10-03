# Rules video

The source for the rules explainer video, `rules-video.mp4` (and its poster,
`rules-video.jpg`) at the repo top level. The video is 16 beats: each beat is a
static 1920x1080 HTML scene plus a Kokoro voiceover line, with animation layers
on top. Every frame is a pure function of time, so a re-render is exact.

## What to edit

- `beats.py`: the beats in order, with each beat's voiceover line (the source of
  truth for the wording and the captions) and a note on what moves.
- `frames/build.py`: the static scene for each beat (map, cards, timeline,
  etc.), keyed by the beat ids in `beats.py`. Reads the game data at the repo
  top level.
- `render/layers.py`: the animation layers that run across beats (the title
  conquest, team dots, the photo, the strategy race).
- `render/build.py`: beat timing (voiceover length plus padding), cross-fades,
  per-beat animation and captions.
- `render/mix.py`: the sound effects and the audio mix.
- `mapdata.py`: the neighborhood map projection shared by the above.

Every rule the video states must match `rules.json`.

## Re-rendering

Run everything from `video/render`. The tools run in Docker. `render/out/`,
`render/poster/` and `render/out_cmd.sh` are gitignored.

1. Build the scenes and compose them. This writes `frames/*.html`, then
   `index.html`, `timeline.json`, `captions.srt` and `vo/lines.json`:

   ```
   python3 ../frames/build.py && python3 build.py
   ```

2. If you changed a voiceover line in `beats.py`, re-synthesize it with Kokoro
   (voice `af_heart`), then run `python3 build.py` again, since the timing
   follows the length of each clip. List only the beat ids you changed; with no
   ids, every line is redone, which takes a while. The `cc-kokoro-hf` volume
   caches the model between runs.

   ```
   docker build -t cc-kokoro kokoro
   docker run --rm -v $PWD:/r -v $PWD/vo:/vo -v cc-kokoro-hf:/hf cc-kokoro \
     python /r/kokoro/tts.py af_heart 5b-blue,5d-flip
   python3 build.py
   ```

3. Optionally, spot-check a few frames in `out/frames/` before the full render.
   Frame n is at n / 30 seconds; add `-e NOCAP=1` to hide captions. A frame
   rendered alone can differ from the full render by faint anti-aliasing.

   ```
   mkdir -p out && chmod 777 out
   docker run --rm --init -e NODE_PATH=/home/pptruser/node_modules \
     -e FRAMES=264,1500 -v $PWD:/work:ro -v $PWD/out:/out \
     ghcr.io/puppeteer/puppeteer node /work/capture.js
   ```

4. Capture every frame to `out/frames/`. This is slow (about 4,000 frames), so
   split it across four containers of 1,100 frames each (`capture.js` stops at
   the last frame; raise 1100 if the video grows past 4,400 frames):

   ```
   for k in 0 1 2 3; do
     docker run -d --rm --init -e NODE_PATH=/home/pptruser/node_modules \
       -v $PWD:/work:ro -v $PWD/out:/out --name cc-render-$k \
       ghcr.io/puppeteer/puppeteer \
       node /work/capture.js $((k * 1100)) $(((k + 1) * 1100))
   done
   ```

   Wait for the `cc-render-*` containers to exit (`docker ps`).

5. Mix the voiceover and sound effects and encode the video to
   `out/clipper-conquest-rules.mp4`:

   ```
   python3 mix.py > out_cmd.sh
   docker run --rm -v $PWD:/work -w /work --entrypoint sh \
     linuxserver/ffmpeg /work/out_cmd.sh
   ```

6. Capture the poster (the title card, frame 264, without captions):

   ```
   mkdir -p poster && chmod 777 poster
   docker run --rm --init -e NODE_PATH=/home/pptruser/node_modules \
     -e NOCAP=1 -e FRAMES=264 -v $PWD:/work:ro -v $PWD/poster:/out \
     ghcr.io/puppeteer/puppeteer node /work/capture.js
   ```

7. Copy the results to the repo top level, where the site serves them:

   ```
   cp out/clipper-conquest-rules.mp4 ../../rules-video.mp4
   cp poster/frames/f00264.jpg ../../rules-video.jpg
   ```

To syntax-check the animation script in `index.html` without a browser:

```
python3 -c "import re; print(re.search(r'<script>(.*?)</script>',
  open('index.html').read(), re.S).group(1))" > /tmp/page.js
docker run --rm -v /tmp/page.js:/page.js:ro node:22-alpine \
  node --check /page.js
```
