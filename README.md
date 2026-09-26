# Clipper Conquest

Clipper Conquest is a Jet Lag–inspired race game for San Francisco. Two teams, Red and
Blue, ride Muni (and walk) to conquer the city's 41 neighborhoods. Every neighborhood has
three challenges; the team with more completions in a neighborhood holds it, ties go to
whoever got there first, and neighborhoods can be stolen until the clock runs out. Players
use their phones: a study guide (map, rules and every challenge), a printable tri-fold
brochure, a rules video, and a game-app prototype.

Publishing the study guide to GitHub Pages is covered in [PUBLISHING.md](PUBLISHING.md).

## Repo layout

| Path | What it is |
| --- | --- |
| `challenges/` | One Markdown file per neighborhood (candidates plus a recommended trio), design notes (`BRIEF.md`) and the build scripts that turn them into data and review pages. |
| `mockups/` | The web front end: `guide.html` (study guide), `v2.html` (game-app prototype), `brochure.html` (generated tri-fold), the map data (`sf_neighborhoods.geojson`, `muni_routes.geojson`, `hood_order.json`), `rules.json` (the single source of truth for the rules). |
| `video/` | The rules explainer video: script, storyboard, render pipeline, and the finished `clipper-conquest-rules.mp4`. |
| `docs/` | Generated. The published copy of the study guide for GitHub Pages. Don't edit it by hand; rebuild it with `docs_build.py`. |
| `docs_build.py` | Rebuilds `docs/` from the sources. |
| `docker-compose.yml` | Serves `mockups/` locally on port 8013. |

## Running the game app locally

The game app today is the prototype `mockups/v2.html`. It is a static page with no
backend. It has to be served over HTTP, not opened as a `file://`, because it fetches its
map data.

**With Docker (primary):**

```sh
docker compose up -d        # http://localhost:8013/v2.html  (study guide: /guide.html)
docker compose down         # stop
```

This runs `caddy:2` with `mockups/Caddyfile.mockups` (which sends `Cache-Control: no-cache`,
so edits show up on a plain refresh), mounts `mockups/` read-only, and restarts
`unless-stopped`. If another container (for example an older hand-started `clipper-mockups`)
already holds port 8013, remove it first
(`docker rm -f clipper-mockups`), or run the compose service on another port:
`CLIPPER_PORT=18013 docker compose up -d`.

**Without Docker (fallback):**

```sh
cd mockups && python3 -m http.server 8013    # http://localhost:8013/v2.html
```

To try it on a phone, open `http://<this machine>:8013/v2.html` from the same network.

## State and persistence

The prototype keeps all game state in each phone's browser `localStorage`:

| Key | Contents |
| --- | --- |
| `cc2-profile` | This player's name and team |
| `cc2-state2` | Completion timestamps per neighborhood, challenge and team |
| `cc2-photos` | Photo proof as downscaled JPEG data URLs |
| `cc2-end` | The game's end time (the countdown) |
| `cc2-view` | The last view shown (map, challenges or timeline) |
| `cc2-hood` | The neighborhood last shown on the Challenges tab |

State is not shared between players: each phone has its own copy. It survives a page
reload or a browser or app crash on the same phone, and it is lost if the browser's
site storage is cleared. The "Reset demo data" button on the join screen deletes all six keys. A
real game needs a shared backend, which isn't built yet.

### Planned game server (not built yet)

This design is planned but not built. The server is one small process with no database
server:

- Every event, such as a challenge completion (with a timestamp assigned by the server) or a
  photo upload, is appended to an append-only JSON-lines log on a persistent volume.
  The log is fsynced after every write.
- Photos are stored as files next to the log.
- On startup the server replays the log to rebuild the game state, so the process can
  crash and restart at any time without losing anything.
- Clients send a unique event ID with each completion, so a retry after a crash never
  counts twice.
- The whole thing runs in Docker, with the data directory mounted as a volume.

## Rebuilding the generated pieces

A challenge can show a photo of its spot in the guide and the game app. Put the image in
`mockups/img/` (about 960px wide) and add two lines to the challenge in `challenges/*.md`:
`- **Image:** coit-tower.jpg` and `- **Image credit:** who took it, and its license`. Use
only your own photos or openly licensed ones (for example public domain or Creative Commons
from Wikimedia Commons), since the site is public. Open the guide or the app with
`?demo-photos` to see placeholder tiles for the challenges that don't have a photo yet.

All scripts can be run from any directory.

| Command | When to run it | What it writes |
| --- | --- | --- |
| `python3 challenges/build_guide_data.py` | After editing any `challenges/*.md` | `mockups/challenges.json` (the recommended trios, read by the guide and the game app; type, time and cost stay out of it) |
| `python3 mockups/sync_rules.py` | After editing `mockups/rules.json` | The rules block in `mockups/guide.html` (the game app links to the guide instead) |
| `python3 mockups/build_brochure.py` | After a challenge or rules change | `mockups/brochure.html` (the local copy, with the QR code from `mockups/qr_codes.json`) |
| `python3 challenges/build_artifact.py` | When the challenge review page needs refreshing | `challenges/review_artifact.html` (the claude.ai review artifact, which must be republished separately) |
| `python3 docs_build.py https://USERNAME.github.io/clipper_conquest/` | Before publishing | Runs the first three scripts, generates a QR code for the public URL (`mockups/qr_codes.public.json`) and rebuilds `docs/`. See [PUBLISHING.md](PUBLISHING.md). |

After rebuilding the brochure, check that it still prints on 2 pages (for example with
headless Chrome, `--print-to-pdf`, then `pdfinfo`).
