# Clipper Conquest

Clipper Conquest is a Jet Lag–inspired race game for San Francisco. Two teams,
Red and Blue, ride Muni (and walk) to conquer the city's 41 neighborhoods. Every
neighborhood has three challenges; the team with more completions in a
neighborhood holds it, ties go to whoever got there first, and neighborhoods can
be stolen until the clock runs out.

There are four pieces: the study guide (with its printable brochure and rules
video), the game app, the game server, and the replay site for after the game.

## The files

The pages:

- `index.html`: the study guide: the rules, the rules video, the map with every
  neighborhood's challenges, and a button that prints the brochure.
- `app.html` and `app.js`: the game app. `app.js` is the live side: syncing with
  the server, photo uploads, joining a team, location pings.
- `replay.html`: the replay site. It opens an exported game in the browser
  (nothing is uploaded): a map-and-timeline view on a computer, the phone view
  on a phone.
- `mobile.js` and `mobile.css`: the phone view shared by the app and the replay
  site: the map, the Challenges and Timeline tabs, and the after-game replay.
- `replay-core.js`: shared by all the pages: picking the playable challenges out
  of `challenges.json`, opening replay files, who held what when, and the
  winner.
- `brochure.html`: the printable tri-fold, made by `build_brochure.py`.

The data:

- `challenges.json`: every challenge. See "Writing challenges" below.
- `rules.json`: the rules. The guide shows them and the brochure prints them.
- `sf_neighborhoods.geojson` and `muni_routes.geojson`: the map.
- `rules-video.mp4` and `rules-video.jpg`: the rules video and its poster. How
  it's made and re-rendered is in [video/README.md](video/README.md).

The server: `server.py`, its test `server_test.py`, `Dockerfile` and
`docker-compose.yml`. Game data goes in `game-data/`, which git ignores.

`.donotsubmit/` holds drafts and experiments; git ignores it.

## Running a game

The game server is one Python file with nothing to install (Python 3.9+). It
keeps the game and serves the game app at its main address, and nothing else:
only the app and the files it loads, never the game data. The guide and the
replay site live on GitHub Pages (see "Publishing").

```sh
docker compose up -d --build     # players: http://localhost:8080/
                                 # admin:   http://localhost:8080/admin
docker compose down              # stop; the game stays in game-data/
```

Without Docker: `python3 server.py`. Either way, locally the server serves the
files as they are, so edits show up on a refresh.

To preview the guide and the replay site locally, serve the folder with any
static server on another port, for example `python3 -m http.server 8000 --bind
127.0.0.1`, then open http://localhost:8000/ and
http://localhost:8000/replay.html. Keep it bound to your own machine: a plain
static server hands out every file in the folder, including `game-data/`.

The admin page (`/admin`) is only for times and downloads. It shows the game's
state and countdown, lets you pick the start and end times (they save as you
pick them; the start is locked while the game is on), has Start now and End now
(Start now keeps a later end time, otherwise the game runs 5 hours; starting
again after the end carries on the same game, and its replay covers every
stretch), shows who's connected (each phone checks in every few seconds), and
has the downloads. To try it on a phone, open `http://<this machine>:8080/` on
the same network.

Players join with a name and a team. During the game each phone checks the
server every 5 seconds. Changes and photos wait on the phone until the server
has them (in `localStorage` `cc2-outbox` and IndexedDB `cc2-uploads`), so a
dropped signal or a reload loses nothing. The other team's photos stay hidden
until the end. With HTTPS, each phone also sends its location once a minute,
and everyone's map shows each team as a dot at the average of its players'
latest locations (from the last 5 minutes).

When the clock hits zero, the app becomes the replay: both teams' photos show,
the winner's dot gets a crown, and the map tab gets a time scrubber with each
team's route. The admin page then has the downloads: all the photos (a zip, full
size, named by time, team and challenge) and the replay file. The replay file
opens on the replay site after the server is gone.

### Hosting and HTTPS

The server speaks plain HTTP and reads `PORT` from the environment. For a real
game, host it somewhere with HTTPS: phones only share their location with secure
pages, so location tracking needs it (without HTTPS the game works with location
off). Options: Fly.io or Railway (a Docker app with a small disk and automatic
HTTPS), a small virtual server with Caddy in front, Cloud Run with a Cloud
Storage bucket mounted as the data folder, or a Cloudflare tunnel from home.
Keep exactly one copy of the server running, and download both exports before
tearing it down.

### What the server keeps

In `game-data/`:

- `game.log`: every event as one JSON line (setup, complete, fail, remove,
  photo, photo_remove, ping), only ever appended. The server rebuilds the game
  from it on every start, so it can be killed and restarted at any time; a
  half-written last line from a crash is dropped. Saving is batched to at most
  one write per `--flush-interval` seconds (default 1), and a phone's request
  only succeeds once its event is saved. Phones send their own ids, so a retry
  never counts twice.
- `photos/`: `<photo id>-full.jpg` (the original) and `-web.jpg` (the phone's
  small copy). Photos belong to a team's challenge, any number of them, so
  undoing and redoing a completion keeps them.

### The server's API

- `GET /api/state?team=red`: the game, phase, server time, completions,
  failures, photos (the other team's without an address until the end) and,
  during the game, each team's spot: the average of its players' latest
  locations.
- `POST /api/complete` `{id, team, hood, ci, by}`: log a completion; the server
  stamps the time.
- `POST /api/uncomplete` `{team, hood, ci}`: undo your team's completion, while
  the game is on.
- `POST /api/fail` `{id, team, hood, ci, by}`: mark a one-shot challenge as
  failed. The team can't complete it until it undoes that.
- `POST /api/unfail` `{team, hood, ci}`: undo your team's failure, while the
  game is on.
- `POST /api/photo?id=&team=&hood=&ci=&by=&kind=full|web`: upload a JPEG for
  your team's challenge (the body is the image).
- `POST /api/photo/remove` `{photo}`: remove a photo.
- `POST /api/ping` `{team, by, lat, lon}`: a location ping, while the game is
  on.
- After the end, for everyone: `GET /api/replay.json`, the finished game the app
  replays.
- `/admin` and `/api/admin/…`: the admin page and its actions. There's no key:
  anyone with the server's address can use them.

`python3 server_test.py` plays a short game against a real server process,
including a hard kill and a damaged log, and checks that nothing but the pages
can be downloaded.

## Publishing

GitHub Pages publishes the repo's top folder: in the repo's Settings → Pages,
deploy from the `main` branch, folder `/ (root)`. The guide is then at
https://mwhittaker.github.io/clipper_conquest/ (the address on the brochure's QR
code; don't rename the repo after printing), and the replay site at
`…/replay.html`. The app is there too, but without a game server it just points
to the replay site. Pages redeploys on every push.

## Writing challenges

Every challenge lives in `challenges.json`, neighborhoods in map order. Per
neighborhood: `intro`, `why_chosen` and all `candidates`. The first three
candidates are the ones played, in play order; the rest are alternates. Each
candidate has `num`, `title`, `do` (the rules, including exactly when it's
done), `where`, `time`, `cost`, `failable`, `type` (its mechanic family),
`photo` (what to shoot) and `why_here`. The played three also have `lat` and
`lon`, the exact spot the guide pins on the map, and most have `place_id` and
`place_name`, the Google Maps place its Where link opens (spots with no place,
like a street or a stretch of beach, link to the pin). Place IDs can go stale:
refresh them if they're more than a year old or a business moves. `**bold**` and
`*italic*` work in the text. Players only see the first three, and only the
title, rules, where, whether a miss can be retried, and the photo of the spot;
the rest stays off the pages (though the file itself is public).

What makes a good challenge:

- **There's a game in it.** Something to be good at, a decision, or tension:
  teammates with hidden information, deduction from the surroundings, a skill
  mini-game, a committed guess. A plain "go there" only for a spectacular or
  hard-to-reach place, about one per neighborhood, and never "go somewhere and
  take a silly photo".
- **It's inside its neighborhood.** The spot (its `lat`/`lon`) must fall inside
  the neighborhood's outline in `sf_neighborhoods.geojson` (a spot out on a pier
  or jetty, past the outline, counts as the shore it's off); landmarks near a
  boundary are easy to get wrong.
- **It could only happen here.** Anchored in the neighborhood's own places,
  history or oddities; if it works two neighborhoods over, sharpen it.
- **Anyone can judge it.** Completion is objective: a count, a reached spot, a
  matched pose. Never "the best" or "something beautiful".
- **It can't be gamed.** No reason to fail on purpose (the teams play together,
  so no hide-and-seek). A number to guess must be unknowable in advance, like
  people passing a spot, not a fact you can look up. A retry must cost real work
  (move, buy something new) or time; otherwise make it one-shot.
- **No prior knowledge.** Skill, observation, memory studied on the spot,
  teamwork and luck are fine; knowing a fact or a location ahead must not decide
  it.
- **It fits the day.** All-ages, nothing embarrassing or risky, nothing that
  needs BART or running. $0 by default, up to about $10 when the purchase is the
  fun. Reliable on a weekend afternoon (prefer things that are always there).
  5–20 minutes once you're in the neighborhood.
- **Most can't be failed.** Per neighborhood at most one one-shot and one
  retry-style challenge, never all three failable, and at most one that depends
  on strangers.
- **Moments are phone-free.** A challenge that's about taking a moment (five
  minutes somewhere, a silence, reading) says phones away the whole time; one
  teammate may set a timer first and pocket it.
- **Variety.** Spread the mechanic families across the city (charades, memory,
  two counters who must agree, word games, dexterity, ...), and go easy on
  called shots and guess-then-measure. The three played mix places and vibes and
  take roughly 20–45 minutes together.

## After changing challenges or rules

Rebuild the brochure with `python3 build_brochure.py` (everything else reads
`challenges.json` and `rules.json` directly), and check it still prints on 2
pages (for example headless Chrome, `--print-to-pdf`, then `pdfinfo`). The QR
code for the guide's address is saved in `build_brochure.py`.
