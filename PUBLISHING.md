# Publishing the study guide (GitHub Pages)

`docs/` is the published site: `index.html` (the guide), `brochure.html` (the print
brochure, which the guide's "Print the brochure" button loads), `challenges.json`,
`sf_neighborhoods.geojson`, `muni_routes.geojson` and `.nojekyll`. Nothing else from
`mockups/` is published (not the app prototype). `docs/` is generated.
Never edit it by hand.

`docs_build.py` rebuilds it and needs python3. If the `qrcode` library isn't installed, it
also needs Docker, because it generates the brochure's QR code in a `python:3.12-slim`
container. That container downloads the library from the internet on first use.

## Decide first

1. **The URL.** For a repo named `clipper_conquest` it is
   `https://USERNAME.github.io/clipper_conquest/`. It is case-sensitive and must end with
   `/`. The brochure's QR code encodes this URL, so choose it before printing anything.
2. **What becomes public.** Free GitHub Pages needs a **public** repo, which publishes
   the whole repo, not just `docs/`. That includes the challenge drafts, the design notes and
   `challenges/JETLAG_EXAMPLES.md` (a challenge list scraped from the Jet Lag fandom wiki).
   If that's not acceptable, use option B below.
3. **The rules video.** The guide does not link or embed it, so it is not published. To
   add it, copy `video/clipper-conquest-rules.mp4` (about 9 MB, fine for Pages) into
   `docs/` from `docs_build.py`, by adding it to `DATA_FILES` with its source path, and
   add a link or `<video>` to `mockups/guide.html`.

## Tonight: option A (publish this repo)

This directory is not a git repo yet. `.gitignore` already leaves out the 400 MB of
rendered video frames.

1. On github.com, create a new **public** repository named `clipper_conquest`. Leave it
   empty: no README, license or .gitignore.
2. Build with the real URL:
   ```sh
   cd ~/github/mwhittaker/clipper_conquest
   python3 docs_build.py https://USERNAME.github.io/clipper_conquest/
   ```
   It must end with `docs/ ready for ...`. It stops with `ERROR` lines if a published page
   references a local URL (for example localhost) or a file that is missing from `docs/`.
3. Commit and push:
   ```sh
   git init -b main
   git add -A
   git status            # check: no video/render/out, no surprises
   git commit -m "Clipper Conquest: study guide + GitHub Pages build"
   git remote add origin git@github.com:USERNAME/clipper_conquest.git
   git push -u origin main
   ```
4. Go to repo **Settings → Pages → Build and deployment**. Set Source to **Deploy from
   a branch**, and set Branch to **main** and folder **/docs**. Save.
5. Wait a minute or two. The **Actions** tab shows "pages build and deployment". Then
   open the URL and check the following:
   - the map draws, and tapping a neighborhood shows its three real challenges
   - "Print the brochure" opens a 2-page print preview
   - scanning the brochure's QR code with a phone opens the guide

## Tonight: option B (keep this repo private)

Create a separate public repo, for example `clipper-conquest-guide`, that holds only the
built site:

```sh
python3 docs_build.py https://USERNAME.github.io/clipper-conquest-guide/
mkdir -p ~/github/mwhittaker/clipper-conquest-guide && cd $_
git init -b main
cp -r ../clipper_conquest/docs .
git add -A && git commit -m "Publish study guide"
git remote add origin git@github.com:USERNAME/clipper-conquest-guide.git
git push -u origin main
```

Then do steps 4 and 5 above (branch main, folder /docs). To update later, rerun
`docs_build.py`, replace the `docs/` folder in that repo (`rm -rf docs && cp -r
../clipper_conquest/docs .`), then commit and push.

## Updating later

After editing challenges (`challenges/*.md`) or rules (`mockups/rules.json`):

```sh
python3 docs_build.py https://USERNAME.github.io/clipper_conquest/
git add -A && git commit -m "Update guide" && git push
```

Pages redeploys on every push, usually within a minute. The guide fetches
`challenges.json` with a cache-buster, so players see the new challenges on a plain reload.

## Notes

- `mockups/qr_codes.json` holds the QR code used by the local brochure build. `docs_build.py` never changes it. The public QR code is cached in
  `mockups/qr_codes.public.json` and regenerated only when the URL changes.
- Printed brochures point at the URL permanently. Don't rename the repo after printing.
- Custom domain: add `docs/CNAME` and set it under Settings → Pages. `docs_build.py`
  keeps `CNAME` and deletes everything else in `docs/`. Rerun it with the new URL so the
  QR code matches.
