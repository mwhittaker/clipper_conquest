# Clipper Conquest — rules explainer (script v2)

Target length: ~2:10. Voiceover (VO) + on-screen animation, in the guide/app look (white,
system type, water-blue map panel). Every rule stated here must match
`mockups/rules.json`. The video covers the core game only; the full rule list and every
challenge live in the guide.

Teams: **Red** (#C42847) and **Blue** (#1D6FB8). Example neighborhoods are real and in
the game. Storyboard frames: `video/frames/` (built by `video/frames/build.py`). The beat-by-beat
voiceover and motion notes live in `video/storyboard.py` (BEATS) — that list is the source
of truth for exact wording; this file is the section outline.

---

## 1. Cold open (0:00–0:10) — frame 01

**Screen:** White. A Clipper-card *tap* sound. The SF map draws itself outline by
outline, 41 shapes in quick succession, then a few fill red and blue. Title slides in:
Clipper (blue) / Conquest (red). *Tap on. Take over.*

**VO:** Two teams. Forty-one neighborhoods. One clock. This is Clipper Conquest.

## 2. The basic idea (0:10–0:30) — frame 02

**Screen:** The map, all neighborhoods grey. They light up in a quick ripple as the VO
counts. Zoom to North Beach, which turns selection-yellow; three challenge cards slide in
beside it, exactly like the guide.

**VO:** Clipper Conquest is played by two teams that race to conquer as many San
Francisco neighborhoods as possible. Whichever team has more neighborhoods when the clock
hits zero is the winner. Every one of the
city's 41 neighborhoods has three unique challenges. Things like: get three antique arcade
machines running at once, count the sea lions with a teammate, or just climb to Coit
Tower.

## 3. Getting around: Muni only (0:30–0:45) — frame 03

**Screen:** Pull back to the whole map. Muni rail, streetcar, cable car and Rapid lines
draw across it in their real colors. A red team dot rides the F-line along the
waterfront and the Powell–Mason cable car to North Beach. Beside the map, a checklist: buses, Muni
Metro, streetcars, cable cars ✓ — BART, Caltrain, cars, bikes ✗.

**VO:** You get around on Muni, and only Muni. Buses, Metro, streetcars, cable cars.
No BART, no Caltrain, no cars, no bikes. And no running — speedwalk.

## 4. Proof: every completion needs a photo (0:45–1:05) — frame 04

**Screen:** Back in North Beach. A phone slides up showing the app on Balmy Alley
Bestiary. A camera shutter *click*: a photo of Coit Tower drops into the challenge.
A thumb taps the big red **Complete** button; it turns into a check with the time, 11:58,
and a small upload bar fills. On the map behind the phone, North Beach's score ticks up.

**VO:** When you finish a challenge, take a photo — every completion needs one — and log
it in the app. The moment you log it is the moment it counts.

## 5. How you conquer (1:05–1:30) — frame 05

**Screen:** Stay on North Beach, app-style timeline feed beside it. Score starts
`Red 0 · Blue 0`, neighborhood grey.

**VO:** You conquer a neighborhood by completing its challenges. Whoever has completed
more of them holds it.

**Screen:** 11:04 — Blue logs one. North Beach floods blue: `0–1`.

**VO:** Blue completes one. One to nothing — North Beach is Blue's.

**Screen:** 11:40 — Red logs one: `1–1`. 11:58 — Red logs another: `2–1`. North Beach
flips red; the feed highlights "Red takes North Beach."

**VO:** Red completes one, then another. Two beats one. Red steals North Beach.

**Screen:** 12:30 — Blue logs its second: `2–2`. Freeze. North Beach fills with red and
blue stripes.

**VO:** So what happens on a tie?

## 6. The tiebreak (1:30–1:50) — frame 06

**Screen:** The feed becomes a timeline: Blue at 11:04 and 12:30, Red at 11:40 and 11:58.
A marker sweeps across; at 11:58 a flag pops: *Red reaches 2 first*.

**VO:** Ties go to whoever got there first. Red logged its second challenge at 11:58;
Blue didn't get there until 12:30. So on a two–two tie, Red keeps North Beach.

**Screen:** Cut to Hayes Valley. Blue logs all three — check, check, check — and a lock
snaps shut over it.

**VO:** Complete all three and it's yours for good. Even if the other team matches you,
you got there first.

## 7. Strategy: stealing (1:50–2:05) — frame 07

**Screen:** Full map mid-game, red and blue patchwork. Every Blue neighborhood shows how
many challenges Red would need to flip it: yellow 1s and 2s, white 3s, black locks. A
bold red route runs through three cheap Blue neighbors in a row — Western Addition,
Japantown, Marina — flipping each one as it passes.

**VO:** The fastest way to gain ground is often to take it. Look for neighborhoods the
other team only barely holds — especially a few in a row — and go steal them. And guard
your own: one more challenge where you're ahead makes you a lot more expensive to rob.

## 8. Close (2:05–2:12) — frame 08

**Screen:** The map settles; the score bar shows the clock running. End card: Clipper /
Conquest and the guide's QR code with "Every rule and every
challenge: the guide."

**VO:** Most neighborhoods when the clock hits zero wins. Every rule and every challenge
is in the guide.

---

### Open questions for the host
- Game length on the clock (frames use placeholder times).
- Voice: Piper (local, free), your own recording, a cloud voice (API key), or captions only.
- Music/sfx: Clipper tap sound as the signature beat?
