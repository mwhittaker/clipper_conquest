# Clipper Conquest — Challenge Design Brief

Context: a Jet Lag: The Game–inspired race across San Francisco. Two teams (Red vs Blue,
2–6 people each, **including kids**) race to conquer the 41 official SF Analysis
Neighborhoods. Each neighborhood has 3 challenges; the team that completes more of them
holds the neighborhood (ties broken by who got there first); territories can flip.
Timed game, played on a **weekend, during the day**. Phones are used to mark completions
and upload a required proof photo — but players are friends, so the photo is really a
memory/highlight, not anti-cheat.

## What the research says makes challenges great

From Jet Lag itself (e.g. "win a carnival game at Luna Park", "flip a coin at the Royal
Australian Mint and call it 8 times in a row", "trap a bug in Vegemite", "swap the
fillings of a ravioli and an Oreo and eat both"):
- **Place-anchored beats generic.** The best challenges could only happen *here*. The
  place itself (a mint, a carnival) does half the comedy.
- **Objective, binary outcomes.** You won the carnival game or you didn't. Completion is
  never a judgment call.
- **A little absurdity, physically enacted.** Doing a slightly ridiculous thing in a real
  public place is the show's engine — but for us it must stay kid-friendly and
  non-embarrassing (fun-silly like recreating a statue's pose: yes; performative
  spectacle: no).
- **Tension mechanics sparingly**: coin-flip-style one-shot challenges are thrilling
  precisely because most challenges aren't like that.

From scavenger-hunt design (GISHWHES, Watson Adventures, corporate hunts):
- **Specific prompts beat vague ones.** "Find the plaque that mentions a ship" beats
  "learn some history".
- **The photo IS the product.** Design the completing moment to be a great picture.
- **Counting/finding/matching tasks** ("find 5 different X", "match this photo to where
  it was taken") are reliable, all-ages, and self-verifying.
- **Recreate/imitate tasks** (poses, album covers, paintings) photograph wonderfully.

## Hard rules for every challenge

1. **Kid-friendly, family-appropriate.** No alcohol, no bars-as-destination, nothing
   embarrassing, nothing risky. Light physical activity fine (stairs, hills, a short
   walk); nothing strenuous.
2. **Free or cheap.** $0 default; up to ~$10 per challenge is fine when the purchase IS
   the fun (a pastry, a trinket, an arcade token).
3. **Weekend-daytime reliable.** Prefer things that exist 24/7 (murals, stairs, views,
   parks, statues, storefronts-from-outside). A shop/venue dependency is OK only if it's
   reliably open weekend daytime — and only for a really good challenge.
4. **5–20 minutes** once you're in the neighborhood (travel time between neighborhoods
   doesn't count).
5. **Objective completion.** A referee who wasn't there could look at the photo/claim and
   say yes/no. Counts, named objects, reached locations, completed transactions,
   matched poses. NEVER "the best", "something beautiful", "impress us".
6. **Not stranger-dependent by default.** Talking to strangers may appear in AT MOST one
   candidate per neighborhood, and never in more than one of your top 3.
7. **Luck in moderation.** A spot-the-parrot style challenge is fine occasionally; a
   challenge that's pure dice is not.
8. **Failability mix** (teams can mark a challenge failed; some allow retries):
   - Most challenges: **achievable with persistence** (can't be permanently failed).
   - Per neighborhood at most ONE **one-shot** (fail = done, e.g. "call the coin flip")
     and/or ONE **fail-and-retry** (attempt-based). Never all three failable.
9. **Photo moment designed in.** Say what the proof photo shows; make it a keeper.
10. **Unique to the neighborhood.** Anchor in its defining places, history, geography,
    food, oddities. If your challenge would work equally well two neighborhoods over,
    sharpen it. (Research the neighborhood before writing!)
11. **Practical safety/comfort**: stick to well-trafficked, daytime-comfortable blocks
    and places; this is a family game.

## Output format (exactly this structure, in your assigned file)

```markdown
# <Neighborhood name>

<2–4 sentence neighborhood character sketch: what defines it, what you anchored on.>

## Candidates

### 1. <Punchy challenge title>
- **Do:** <precise, objective instructions incl. completion condition>
- **Where:** <specific place(s)/area, cross-streets if useful>
- **Time:** <est. minutes> | **Cost:** <$0 / ~$X>
- **Failable:** no / retryable (<what counts as an attempt>) / one-shot
- **Photo:** <what the proof photo shows>
- **Why here:** <one line tying it to the neighborhood>

### 2. ...
(5–6 candidates total)

## Recommended trio

**<n>, <n>, <n>** — <one or two sentences on the mix: variety of place within the
neighborhood, at most one failable, at most one stranger-y, spread of vibes
(find/do/make/climb/taste), and total time for all three ≈ 20–45 min.>
```

Quality bar: these will be reviewed side by side across all 41 neighborhoods. Generic
filler ("take a selfie somewhere nice") will be cut. Every candidate should make someone
reading the list say "oh that's fun" or "wait, that exists?"

## v2 quality bar — "where's the game?" (added after the FiDi rework)

The first draft produced too many **errands**: go somewhere, buy something, photograph
something. The bar now, calibrated on Jet Lag's real challenge corpus (see
JETLAG_EXAMPLES.md, 443 scraped examples):

- **Most challenges must contain a game**: something to be good at, a decision, or
  tension. The four flavors we use: teammate roles + hidden information (blindfold
  tastes, describe-and-find), deduction from the environment, skill/dexterity
  mini-games, and called-shot gambles (commit to a prediction BEFORE looking).
- **Design the commit moment.** State precise stakes in the rules: attempt counts,
  one-touch answers, margins ("within 10%"), cooldowns ("miss = wait for the next
  streetcar"), and "you may not practice" where it matters.
- A plain "go there / do the thing" is still allowed when the place is genuinely
  spectacular or hard to reach, or the act itself is the fun — but it's the exception,
  roughly one per neighborhood at most.
- Everything else still applies: kid-friendly, ≤$10, weekend-daytime, 5–20 min,
  objective completion, photo designed in, at most one stranger-y candidate.
- Exemplar: fidi.md (The Blindfold Market / Mind the Doors / Heart Detective).
- **Partial participation is fine.** A challenge may use only some teammates (two
  walkers, one taster, one counter pair); no need to involve the whole team in every
  task.
- **No prior-knowledge challenges.** The host reviews every challenge, so nothing may
  hinge on knowing a fact, price, or location in advance (no "guess what it sold for",
  no "find X without maps" where knowing the spot is the whole puzzle). Skill,
  observation, memory studied on-site, teamwork, and luck are all fine.
