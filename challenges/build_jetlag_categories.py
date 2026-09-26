#!/usr/bin/env python3
"""Build jetlag_categories.html: every Jet Lag challenge in JETLAG_EXAMPLES.md sorted
into mechanic families, with notes on which families Clipper Conquest already uses.

The categorization is hand-curated (CATS below); the corpus file is only used to
sanity-check the count. Run: python3 build_jetlag_categories.py
"""
import html, re, pathlib

HERE = pathlib.Path(__file__).parent

# Season tags
S = {
    'AU': 'Au$tralia', 'B4A': 'Battle 4 America', 'CIRC': 'Circumnavigation',
    'C4': 'Connect Four Across America', 'JPN': 'Japanorama',
    'NZ': 'Race to the End of the World', 'SCH': 'Schengen Showdown',
    'KOR': 'Snake Across South Korea', 'SS': 'Stateside Scramble',
    'TAG': 'Tag Across Europe', 'TAG2': 'Tag Across Europe 2',
    'TAGA': 'Tag Across Europe All Stars', 'TW': 'Taiwan: Rail Rush',
    'CTF': 'Capture the Flag (Japan)', 'ARC': 'Arctic Escape',
}

# (title, season, one-line gist)
CATS = [
 ('guess', 'Guess, then measure', 'estimation wagers',
  'Commit to a number first, then find out. The reveal is the fun; a tolerance band makes it fair.',
  'Lyon Street foot traffic (Pac Heights), Yoda\'s height (Presidio), quarter-pound of candy (Hayes), '
  'Flora Grubb price (Bayview), China Beach stairs (Seacliff), 60-second fuse (Glen Park), '
  'hedge paces (Pac Heights), key count (Vis Valley).',
  [
   ('Calculate Boba', 'AU', 'one minute to estimate the boba in your tea; within 10%'),
   ('Be Familiar with Your Teammate\'s Game', 'AU', 'predict a teammate\'s sprint time; within 15%'),
   ('Sense the Passage of Time', 'AU', 'stop a hidden timer within 3 min of the 30-minute mark'),
   ('Measure a Mile on the Wheel of Brisbane', 'AU', '(no description on the wiki)'),
   ('Kill Time, Then Tell Time', 'SCH', 'do three time-killers, then guess elapsed time within 5 min'),
   ('Estimate Your City\'s Population', 'TAG', 'one guess, within 25%, no phone'),
   ('Choose Your Own Adventure', 'TAG2', '50 burpees OR estimate the population within 25%'),
   ('Abridge a Bridge', 'SS', 'estimate a covered bridge\'s length within 10% without crossing'),
   ('Estimate a Lake', 'SS', 'guess a Minnesota lake\'s acreage within 10%'),
   ('Estimate the Diameter of the Hakka Roundhouse', 'TW', 'body-only measurement, within 20%'),
   ('Get Your Qi Flowing at a River', 'TW', 'meditate for a chosen time and stop within a minute'),
   ('Take to the Skies', 'TAGA', 'launch something and predict its air time; under-predict or void'),
   ('Complete a Jellyfish Census', 'TW', 'two independent counts must land within 25% of each other'),
  ]),
 ('predict', 'Call your shot', 'predictions about the world',
  'Predict something you can\'t control — a bus, a train door, a stranger\'s photo — then watch it resolve.',
  'Call the 38 (Western Addition), Tunnel Roulette K/L/M (West of Twin Peaks), BART car count (Outer Mission), '
  'Bridge or No Bridge (Twin Peaks), capsule color (Japantown), carousel animals (GG Park), pizza toppings (Inner Sunset), '
  'meeting point on the ghost track (OMI), Mind the Doors (FiDi), Call the Crossing (Nob Hill).',
  [
   ('Predict Market Flow at Adelaide\'s Central Market', 'AU', 'customers at a stall in 10 min; within 40%'),
   ('Predict a Popular Brighton Beach Bathing Box', 'AU', 'which of two boxes gets photographed next'),
   ('Predict the Train Doors', 'AU', 'stand where the doors will stop'),
   ('Bet on 5 Surfers', 'AU', 'pick surfers who\'ll stand 3 s; 3 of 5 must'),
   ('Predict a Point of Beach Volleyball', 'AU', '(no description on the wiki)'),
   ('Predict Boarding Passengers', 'KOR', 'will anyone board your car at this stop?'),
   ('Predict Door-Open Seconds', 'KOR', 'how long will the doors stay open; within 25%'),
   ('Be in the Hot Seat', 'TW', 'call how many trivia answers you\'ll get in 60 s'),
   ('See a Predictable Number of Monkeys', 'TW', 'call the monkey count before climbing Monkey Mountain'),
   ('Play Boba Blowdarts', 'TW', 'call how many tapioca balls you\'ll catch in a cup'),
  ]),
 ('meld', 'Mind meld', 'teammate agreement without collusion',
  'Two people, no talking, must land on the same answer. Rewards knowing your teammate.',
  'Two-counter agreement (Quesada palms, Bison Paddock, Alta Plaza stairs, St. Mary\'s canopy), '
  'sea lion count (North Beach), Spanish Steps step count (USF), labyrinth felt-time match (Nob Hill).',
  [
   ('Mind Meld at the Brisbane Sign', 'AU', 'partner picks a letter; you get three guesses'),
   ('Mind Meld at a Tokubetsu Meishō', 'JPN', 'each lists five beautiful things; 3 of 5 must match'),
   ('Mind Meld at a Skyscraper', 'SS', 'sort photos into prettiest/ugliest/silliest/most-like-partner'),
   ('Shoot the Gap', 'KOR', 'collect objects; the middle count wins'),
   ('Complete a Jellyfish Census', 'TW', 'independent counts within 25%'),
   ('Find the Jet Laggers at the Chrysanthemum Festival', 'TW', 'match four art pieces to four players'),
   ('Appreciate Your Surroundings', 'SCH', 'one lists ten things, the other draws; all ten must appear'),
   ('Taste Test Strawberries', 'JPN', 'predict how your partner will rank three berries'),
  ]),
 ('relay', 'Secret message', 'encode it, send it, decode it',
  'One teammate knows a word or a target; it has to reach the other through a narrow channel — Morse, flags, a light, five words, yes/no answers, a blindfold.',
  'Origami crane by voice (Japantown), telephone up Harry St (Glen Park), stage whisper (McLaren), '
  'semaphore letters (Twin Peaks), five-word cover (Haight) and mansion (Pac Heights), Taboo on the bridge (Western Addition), '
  'human sculpture by words (Hayes).',
  [
   ('Read Signal Flags at Mount Nelson', 'AU', 'spell a 10-letter word in flags from 100 ft'),
   ('Send a Telegraph', 'AU', 'build a Morse device; transmit a 5-letter word 10 ft'),
   ('Communicate by Morse', 'ARC', 'random 8-letter word in Morse from 20 ft'),
   ('Illuminate Your Teammate', 'SS', 'five-letter word using only a light, 100 ft apart'),
   ('Write a Word on Strava', 'ARC', 'run a 4-letter word as a GPS trace until guessed'),
   ('Teach From Afar', 'AU', 'deliver a written fact 40 ft to a teammate who can\'t move'),
   ('Demonstrate Synesthesia', 'TW', 'one word to convey a color; partner steps onto the right stair'),
   ('Pitch a Painting', 'TW', 'describe a photo; partner finds the mural in the village'),
   ('Build a LEGO Set Blind', 'SCH', 'blindfolded builder, sighted instruction-reader'),
   ('Play Suikawari', 'JPN', 'spun and blindfolded, hit the watermelon on three words of guidance'),
   ('Lead Your Teammate Through the Jungle, Blindfolded', 'NZ', 'guide a blindfolded partner along a trail'),
  ]),
 ('actguess', 'Act it, draw it, guess it', 'charades and pictionary',
  'Make a depiction — with your body, a pencil, pebbles, butter — and someone else has to name it. No channel constraint, just craft.',
  'Bronze Age Charades (Mission Bay), Painted Lady charades (Hayes), Last Supper charades (Excelsior), marquee charades (Western Addition), '
  'silent movie (Vis Valley), dune Pictionary (Lakeshore), Masterpiece One Guess (Marina), Pose Detective (Mission).',
  [
   ('Impersonate Your Foes', 'TAGA', 'charades all four opponents in order in one minute'),
   ('Make a Rock Engraving', 'AU', 'carve a random animal; teammate guesses first try'),
   ('Make a Recognizable Portrait', 'AU', 'draw a portrait; the audience must guess the subject'),
   ('Draw George Washington', 'B4A', 'portraits judged by Twitter poll'),
   ('Sculpt a Butter Animal', 'SS', 'audience must guess the animal'),
   ('Create the Creation of Adam', 'SCH', 'paint above your head; audience must identify it'),
   ('Discover Your Zodiac(s)', 'TW', 'depict zodiac animals in 50 pebbles for a teammate to guess'),
   ('Take an Iconic Photo at a National Park', 'SS', 'followers must guess which park'),
   ('Find a Statue and Recreate It', 'C4', 'hold the pose five minutes (no guessing — borderline)'),
  ]),
 ('words', 'Word & language games', 'spelling, forbidden words, translation',
  'The constraint is linguistic: don\'t say these words, spell that one, decode this script.',
  'Spelling bee at the witch\'s house (Pac Heights), spell CLIPPER (Noe), book spines R-E-D / B-L-U-E (Inner Richmond), '
  'twenty questions (Castro), the word "San Fran" fortune (Chinatown).',
  [
   ('Claim the State Immediately, But…', 'C4', 'book a flight by phone without 14 forbidden words or any city name'),
   ('Escape the Train', 'SS', 'guess the secret password with one yes/no question per stop'),
   ('Shake Yes, Nod No', 'SCH', '15 yes/no questions answered with inverted gestures in 100 s'),
   ('Translate This Card', 'CTF', 'decode a card written in Japanese, no photo tools'),
   ('Find a Korean Word and Guess It', 'KOR', 'guess an untranslated word\'s meaning; three tries'),
   ('Gangnam Style into Google Translate', 'KOR', 'recite the opening stanza until 50% is recognized'),
   ('Eat an Alliterative Sandwich', 'ARC', 'five fillings, one letter'),
   ('Spell Your Name in Graffiti', 'ARC', 'each letter from existing graffiti'),
   ('Cursed: No Words With the Letter E', 'NZ', 'three hours'),
   ('Cursed: Spanish Only', 'CTF', 'translate everything into Spanish until tagged'),
   ('Užupian Right: Third Person Only', 'SCH', 'one of the random rights in "Exercise Your Užupian Rights"'),
  ]),
 ('findmate', 'Find your teammate', 'hide, spot, seek',
  'One teammate is somewhere; the other has to spot them, or the seekers have to fail. Hide-and-seek for grown-ups.',
  'Hide-and-seek in Sutro Heights (Outer Richmond); the two-peak semaphore (Twin Peaks) starts with spotting each other.',
  [
   ('Spot Your Partner from a Ropeway', 'JPN', 'find your teammate on the ground from a gondola'),
   ('Observe the Observers', 'TW', 'spot your teammate from Taipei 101 in 5 min'),
   ('Photograph Your Partner from Far Away', 'B4A', 'half a mile, must be visible'),
   ('Bamboozle in Bamboo', 'JPN', 'hide in bamboo; the audience must fail to find you'),
   ('Hide and Seek', 'TAG', 'last an hour hidden from the chasers'),
   ('Locate the Chasers', 'TAGA', 'three map pins; a team within 10 miles scores'),
  ]),
 ('senses', 'Blind senses', 'taste, touch, smell, rank',
  'Blindfold one teammate and make them identify, rank or count with a single sense.',
  'Produce by touch (Portola), fruit by touch — The Hand Knows (Chinatown), Blindfold Market taste-then-find (FiDi). The Salt & Straw taste test was removed.',
  [
   ('Taste Test Australian Foods', 'AU', 'identify 3 of 5 iconic foods blindfolded'),
   ('Distinguish Wines', 'AU', 'red, white, rosé blind'),
   ('Identify Chocolates at Haigh\'s', 'AU', 'name seven fillings'),
   ('Taste Rice at a Rice Field', 'JPN', 'count the grains in your mouth'),
   ('Taste Test Conveyor Belt Sushi', 'JPN', 'rank three pieces by price, blind'),
   ('Sense Pastizzi', 'SCH', 'five pastries, one sense each'),
   ('Do a Taste Test (Haribo)', 'TAG2', 'three gummy bears, all flavors right'),
   ('Buldak Taste Test', 'KOR', 'identify three spicy ramen varieties blind'),
   ('Taste Test Taiwanese McDonald\'s', 'TW', 'one bite, then name the item'),
   ('Taste the Rainbow at Dawu', 'TW', 'six foods, guess each one\'s color blind'),
   ('Buy the Same Thing as Your Teammate', 'AU', 'inspect by touch, then buy the match'),
   ('Taste Test Strawberries', 'JPN', 'predict how your blindfolded partner ranks three berries'),
   ('Blindfolded Chopstick Crackers', 'KOR', '7 of 10 shrimp crackers to your mouth in a minute, blind'),
  ]),
 ('memory', 'Memory', 'study, then recite or retrace',
  'Study as long as you like, then perform with the source hidden. Restart on any slip.',
  'Musing-station recital (McLaren), Greenway ironwork (Vis Valley), jazz pavers (Western Addition), '
  'Fishermen\'s Stone characters (Seacliff), Thirteen-Garden loop (FiDi), Memorize the Nations (Tenderloin), mural quiz (Western Addition alt).',
  [
   ('Memorize the Flags at Commonwealth Place', 'AU', 'identify 8 of 10 random flags from a 110-flag display'),
   ('Remember at the Elephant Rocks', 'NZ', 'touch ten rocks in a random memorized order'),
   ('Sing the Ōkaihau Express', 'NZ', 'memorize and sing a song uninterrupted'),
   ('Learn the Star-Spangled Banner', 'SS', 'memorize a verse on a water taxi while being pelted'),
   ('Memorize Everywhere', 'ARC', 'recite every place in "I\'ve Been Everywhere"'),
   ('Dance Like Nobody\'s Watching', 'ARC', 'perform Amy\'s TikTok dance at tempo, no mistakes'),
   ('Go Birdwatching in Da\'an Park', 'TW', 'memorize 33 birds, then ID one your partner photographs'),
   ('The Floor Is (Mostly) Lava', 'TW', 'memorize the one safe path across the rocks'),
   ('Use TripAdvisor, Then No Map', 'KOR', 'memorize the route to the #1 attraction'),
  ]),
 ('aim', 'Aim, throw, catch', 'projectile skill',
  'A target, a distance, a number of attempts. The most reusable family in the show.',
  'Paper airplanes at Clipper Cove (Treasure Island); claw machine (Lakeshore).',
  [
   ('Throw a Democracy Sausage into a Bun', 'AU', 'catch a sausage in a bun from 30 ft, 5 tries'),
   ('Successfully Throw and Catch a Boomerang', 'AU', ''),
   ('Throw a Shrimp on the Barbie', 'AU', '100 tries, any shrimp on any Barbie'),
   ('Become a Socceroo', 'AU', 'kick a ball into a sock from 20 ft, 10 tries'),
   ('Land a Bottle Right Side Up (Upside Down)', 'AU', 'land it on its cap, 10 tries'),
   ('Flip One of Japan\'s Remarkable Waters', 'JPN', 'bottle flip with spring water'),
   ('Make an Advertisement for Coca-Cola', 'SS', 'both teammates flip a Coke bottle'),
   ('Get a Hole in One', 'AU/B4A/SS', 'mini golf, once per hole'),
   ('Score a Bogey', 'AU/SS', 'real golf'),
   ('Shoot a Bullseye', 'B4A/JPN', 'bow and arrow, 15–20 ft (JPN: inner three rings)'),
   ('Score an Australian Rules Football Goal in Redfern', 'AU', ''),
   ('Waterfall at Huka Falls', 'NZ', 'pour a drink into a teammate\'s mouth from 10 ft up until a cup is 80% full'),
   ('Skip a Stone', 'B4A/NZ', '3 skips over a sunken town; 6 skips at Constant Bay'),
   ('Bowl a Strike', 'C4', ''),
   ('Complete a Haast Pass', 'NZ', 'throw a rugby ball across a river to a teammate'),
   ('Score a Drop Goal', 'NZ', 'through the uprights from 15 m, alternating'),
   ('Throw a Gumboot', 'NZ', '15 m at the official gumboot lane'),
   ('Set a New World Record on Oreti Beach', 'NZ', 'fewest tries to catch a Nerf dart in your mouth from 40 ft'),
   ('Win Milk Pong', 'NZ', 'ping-pong ball into a cup from 8 ft, 5 tries'),
   ('Play Sake Pong', 'CTF', 'six feet, five tries, cup at any height'),
   ('Play Waffle Pong', 'SCH', 'land a candy in every hole of a waffle from 2 m'),
   ('Win Level 1 of Angry Birds', 'SCH', 'build a slingshot, birds, pig and tower; knock the pig down'),
   ('Make a Putt', 'TAG2', 'roll a ball into a cup from 10 ft, one attempt'),
   ('Master Pétanque', 'TAGA', 'roll within 6 inches of the marker from 15 ft, one attempt'),
   ('Win at Tuho', 'KOR', 'throw sticks into a jar from 6 ft'),
   ('Play Deok-su\'s Game', 'KOR', 'marbles into a hole from 5 ft'),
   ('Play Ddakji', 'KOR', 'flip the other paper tile'),
   ('Hit a Home Run', 'KOR', 'anything as bat and ball, 20 ft airborne, 3 strikes'),
   ('Survive the Batting Cage', 'JPN', '3 of 5 pitches'),
   ('Play Pocky Hockey', 'CTF', 'Pocky stick, Pocky puck, into the box in 5'),
   ('Throw a Paper Airplane 30 Consecutive Feet', 'ARC', ''),
   ('Win the Little League World Series', 'SS', 'throw to all four bases in a row, on your knees'),
   ('Kill Each Other in a Duel', 'SS', 'ten paces, "draw", both must hit'),
   ('Wage an Interstate War', 'ARC', 'hit your teammate with pie across a county line'),
   ('Dock a Boat', 'NZ', 'blow a homemade boat 15 m into a one-foot dock'),
   ('Win a Prize from a Claw Machine', 'B4A/KOR', 'unlimited tries / 10 drops'),
   ('Win a Carnival Game', 'AU/B4A', '$20 budget / top-tier prize'),
   ('Keep a Ball Inbounds at 100 Steps of Federation', 'AU', ''),
   ('Play Catch', 'NZ', '10 throws without a drop, 20 ft apart'),
  ]),
 ('balance', 'Balance, carry, dexterity', 'don\'t drop it',
  'Move something fragile from A to B, or keep it up. Restart on a drop.',
  'Wood Line log walk (Presidio), chopstick gauntlet (Inner Richmond), 31.5% tower (Russian Hill), '
  'labyrinth without a wobble (McLaren alt), rainbow crosswalk stripes (Castro).',
  [
   ('Face Tim Tam / Face Cookie', 'AU/ARC', 'forehead to mouth, no hands'),
   ('Carry an Egg Across the Federation Walkway', 'AU', 'egg on a spoon'),
   ('Smuggle Sugar to the Sugarloaf', 'AU', 'half a cup of sugar under your hat for a whole trail'),
   ('Transfer a Cup of Fountain Water', 'CIRC', 'fountain to fountain, no phone, spill ≤ ¼'),
   ('Contribute to a Waterfall', 'ARC', 'a full cup carried ¼ mile, spill ≤ 10%'),
   ('Do a Milk Walkie', 'ARC', '100 ft with a cup of milk on your head'),
   ('Transport Macaroni Down Elbow Lane With Your Elbows', 'NZ', 'in under 30 s, one shot'),
   ('Do 1% of Paul Revere\'s Ride Riding a Whole Lemon', 'SS', 'lemon between your legs'),
   ('Keep Your Balance Across a Continental Plate', 'TW', '200 ft holding a stack of cans by the bottom one'),
   ('Show Off Your Chopstick Skills', 'CTF', '30 grains of rice one at a time'),
   ('Gonggi', 'KOR', 'Korean jacks with five pebbles, level one'),
   ('Handstand for a Minute', 'NZ', 'cumulative, unassisted'),
   ('Limbo in Limbo', 'SCH', 'dice set the bar height and attempts, underground'),
   ('Climb a Tree', 'ARC', '4 ft off the ground'),
   ('Sandboard at Te Paki', 'NZ', 'down a 50-ft dune without falling'),
   ('Go Surfing at Bondi', 'AU', 'stand for four seconds'),
   ('Give Your Teammate a Piggyback Ride', 'CIRC', 'around a park perimeter'),
   ('Become a Spin-Top Champion', 'TW', 'build a top that spins 30 s, one attempt'),
   ('Stack Rocks / Tower Battle', 'TAGA/KOR', 'tallest tower; collapse = zero'),
   ('Build a House of Cards', 'JPN', 'two stories at a thatched farmhouse'),
   ('Pepero Palace', 'KOR', 'four sticks leaning at the top'),
   ('Cut an Orange in Half Using Only This Card', 'TAG2', 'no prying with hands'),
  ]),
 ('build', 'Build & make', 'construct, craft, cook, paint',
  'Make a thing that has to work or be recognizable. Often paired with a guess-the-thing test.',
  'Masterpiece One Guess (Marina), junk boat (Seacliff), sand letters (Sunset), dug Sutro bath (Outer Richmond), '
  'Wave Organ recording (Marina), origami crane (Japantown).',
  [
   ('Build a Car at Albert Park Circuit', 'AU', 'one push, 35 ft, one attempt'),
   ('"Sail" Across Todd River', 'AU', 'a boat that crosses a dry riverbed without touching it'),
   ('Create a Traditional Tasmanian Kelp Basket', 'AU', ''),
   ('That\'s Not a Knife', 'AU', 'cut a Tim Tam in half with anything but a knife'),
   ('Finish a Puzzle', 'AU', '250 pieces in 60 min'),
   ('Build a Raft', 'B4A', 'cross 10 ft of water, both aboard, ≤$50'),
   ('Build a Snowman (on the Beach)', 'B4A/ARC', 'B4A: ≥1 ft, three sections, machine snow OK; ARC: natural snow on a beach'),
   ('Send Rockleberry Finn Down the Mississippi', 'SS', 'a natural-material raft carries a rock 30 ft'),
   ('Pop a Kernel of Corn', 'ARC', 'any means'),
   ('Steal Jimmy Johns\' Crown', 'ARC', 'make and deliver your own sandwich to the driver before the order arrives'),
   ('Spell "HELP" in Rocks on an Island', 'B4A', 'foot-tall letters'),
   ('Forge Great American Art / Paint a Local Landscape', 'B4A/C4/TAG/CTF', '3 colors, 75% of the canvas, 15 min'),
   ('Paint Your Teammate\'s Face as the State Flag', 'C4', ''),
   ('Build and Ride a Go-Kart', 'CIRC', '100 ft downhill without falling apart'),
   ('Go Grocery Shopping in a Soap Box Racer', 'NZ', 'push a teammate between two supermarkets'),
   ('Ride Your Snowboard at a Skate Park', 'NZ', 'add four wheels'),
   ('Make Your Own "Hokitika" Beach Sign', 'NZ', 'foot-tall driftwood sign'),
   ('Egg Drop', 'NZ', 'build a vessel on site; 10 ft, no crack'),
   ('Knit a Square', 'NZ', '2×2 inches in front of a giant sheep'),
   ('Make Cheese', 'NZ', 'milk + vinegar + heat → a marble of curd'),
   ('Devil Eggs at the Devil\'s Staircase', 'NZ', ''),
   ('Make a Plentiful Sandwich', 'NZ', 'items from four stores'),
   ('Become a French Chef', 'TAG2/TAGA', 'emulsify mayonnaise'),
   ('Juice', 'TAGA', 'half a cup, strained, from whole produce'),
   ('Make Sushi', 'CTF', 'roll with rice, protein, seaweed, topping'),
   ('Make S\'mores over an Open Fire', 'B4A', ''),
   ('Build a Paper Boat with a Candle', 'KOR', 'float 5 min, candle lit'),
   ('Play Classical Music on Non-Instruments', 'SCH', 'Ode to Joy, correct pitches, one official take'),
   ('Open an Unpopular Museum', 'SCH', 'recreate three exhibits; strangers must ignore it'),
   ('Build Jason His Dream Bouquet', 'SCH', 'to spec in 30 min'),
   ('Make a Hanko', 'CTF', 'a working stamp of your name'),
   ('Kawaii-ify Your Belongings', 'CTF', 'eyes and mouths on ten items'),
   ('Transport a Pumpkin', 'B4A', 'carve the logo, carry it across a state line'),
  ]),
 ('find', 'Scavenger & find', 'locate things, often with no phone',
  'A checklist or a single needle. Best when the haystack is local and the phone is off.',
  'Capitals-and-countries grid (Excelsior), state streets (Potrero), spell CLIPPER (Noe), book spines (Inner Richmond), '
  'Hill book (Potrero), Bird & Beckett (Glen Park), tool gate (Portola), snake in the mural (Portola), pet cemetery (Presidio), '
  'tombstone gutters (Haight), Diana (Outer Richmond), city line by deduction (Outer Mission), eight dogs (Lakeshore), '
  'zodiac animals (Chinatown), and the spot-the-photo hunts: mosaic match (Excelsior), Heart Detective (FiDi).',
  [
   ('Complete the Japan', 'JPN', 'find 8 of 10 Japanese things from a station in an hour, no phone'),
   ('Complete the Canada Scavenger Hunt', 'SS', '8 of 10 Canadian things in 60 min'),
   ('Catvenger Hunt (×2)', 'JPN/TW', 'cats: sleeping, eating, touching another, above you…'),
   ('Find a Penguin at St Kilda Pier', 'AU', ''),
   ('Find an Indigenous Plane', 'AU', 'locate one specific aircraft in an hour, no research'),
   ('Befriend a Quokka in 15 Minutes', 'AU', ''),
   ('Spot Animals at Alice Springs Desert Park', 'AU', '50 animal points in an hour'),
   ('Find 5 Fish in 5 Minutes', 'AU', 'snorkeling'),
   ('Show the Audience One Monkey / Find a Sika Deer', 'JPN', 'wild animal spotting'),
   ('Find Your Prefectural Bird', 'JPN', 'verify with a birding app'),
   ('Find a Clam / a Starfish / Glowworms', 'JPN/NZ', ''),
   ('Find Ten Green Bras on the Cardrona Bra Fence', 'NZ', ''),
   ('Find the Time at Clapham\'s Clock Museum', 'NZ', 'a display clock within 15 min of correct'),
   ('Find Whanganui and Wanganui', 'NZ', 'three signs of each spelling'),
   ('Identify 10 Plants', 'NZ', 'with a plant app'),
   ('Find a Four-Leaf Clover as a Leprechaun', 'B4A', ''),
   ('Find the Most Foreign License Plate', 'B4A', 'furthest origin in 15 min'),
   ('Photograph the Most Birds', 'B4A', 'in 15 min'),
   ('Catch Three Different Local Bugs', 'C4', 'all at once'),
   ('Collect 3 Mario Kart Items', 'CTF', 'banana, shell, star…'),
   ('Find a Maneki Neko / Meet Your Local Yuru-Chara', 'CTF', ''),
   ('Locate a Looney Tune at Movie World', 'AU', 'photo with a live mascot within an hour'),
   ('Catch an Animal Eating', 'TW', 'film a zoo animal eating within 20 min'),
   ('Find the Secret Spot at a Great Garden', 'JPN', 'find Amy\'s secret location in 10 min, no phone'),
   ('Your Friend Is a Bug', 'KOR', 'arrive at the next node with a live bug'),
   ('Find Seven 7-Elevens (truncated card)', 'CTF', ''),
   ('Celebrate Today\'s Name Day', 'SCH', 'find today\'s name printed somewhere in 30 min'),
   ('Find 3 New Friends', 'CTF', 'three non-bug, non-bird animal species'),
   ('Break Copyright Law', 'CTF', 'four places playing copyrighted audio'),
   ('Find a Fancy Car / an American Flag / a Real Gun', 'TAG/TAG2/ARC', ''),
   ('Find a Non-American Flag', 'ARC', ''),
   ('See Something Old', 'TAG2', 'the oldest verifiable thing in 30 min'),
   ('Find the Town Hall', 'TAG2', '30 min, no phone, no asking'),
   ('Visit the US Consulate', 'CIRC', 'no phone lookup'),
   ('Find Air Conditioning', 'TAGA', 'no phone'),
   ('Find Something Rated 4.3+', 'KOR', 'no map app'),
   ('Find the Mystery Object / Find This Thing!!', 'TAGA/TW', 'Amy\'s hint, 5 min / 1 hour, no phone'),
   ('Find Amy a DJUNGELSKOG', 'SCH', 'find it in IKEA without knowing what it is'),
   ('Master the Dewey Decimal System', 'AU', 'find a specific novel in a library in 3 min'),
   ('Get Upcharged', 'AU', 'find the same item priced higher in a second store'),
   ('Invent, Then Find, a Person', 'TAGA', 'coin-flip five traits, find someone who matches'),
   ('Street Art Scavenger Hunt', 'TW', 'three of Amy\'s characters in 15 min'),
   ('Planespot from Across the Pacific', 'ARC', 'four trans-Pacific aircraft'),
   ('Go to Something Interesting', 'CTF', 'a place with a 100k-view YouTube video, no YouTube'),
   ('Get at Least ½ Mile from Any 7-Eleven', 'CTF', ''),
   ('Get 1,000 ft from Any Building', 'TAG', ''),
   ('Stalk a Bird', 'CTF', 'one bird on camera for five continuous minutes'),
   ('Get Goosebumps Near a Goose', 'AU', 'ten seconds of both in frame'),
   ('Spot a UFO / See a Cow / Find a Moose', 'ARC', ''),
  ]),
 ('luck', 'Pure luck', 'dice, coins, machines',
  'No skill, just nerve. Fun as a one-shot; frustrating as a requirement.',
  'Call It at the Mint coin flips (SoMa), capsule color (Japantown); luck-flavored: wheel-of-fortune scoop (Sunset), carousel bet (GG Park), called slide race (Bernal).',
  [
   ('Win Eight Coin Tosses', 'AU', 'eight in a row, called in the air'),
   ('Get Lucky on Coin Flips', 'TAGA', 'seven heads in a row'),
   ('Bet on Roulette', 'B4A', 'red or black, then a gambling PSA'),
   ('Gamble at a Casino', 'CIRC', 'bet $200 total'),
   ('Win the Lottery in Kaeo', 'NZ', 'roll a die, buy that many scratchies'),
   ('Dig a Lucky Hole', 'NZ', 'die × 6 inches deep'),
   ('Take a Lucky Swim', 'NZ', 'roll until 1–3; every 4–6 is a swim'),
   ('Complete a Sisyphean Task', 'SCH', 'carry the boulder uphill until you roll a 17'),
   ('Let\'s Make a Deal', 'TW', 'pick the right one of three towers'),
   ('Gachapon Collecting', 'KOR', 'three different items from one machine on a budget'),
   ('Test Your Luck at the Dragon and Tiger Pagodas', 'TW', 'rock-paper-scissors across two towers, no collusion'),
  ]),
 ('eat', 'Eat & buy', 'consume, purchase, exact spend',
  'Food is the easiest proof there is. The good ones add a constraint: exact change, a category, a place.',
  'Wheel-of-fortune scoop (Sunset), pizza topping bet (Inner Sunset), Eat Something With a Face (Japantown), '
  'exact $5 at Shaw\'s (West of Twin Peaks), dim sum (Inner Richmond), candy by weight (Hayes), It\'s-It (Outer Richmond alt).',
  [
   ('Spend Exactly 940 Yen', 'CTF', 'listed prices, cash, no weight items'),
   ('Spend $100 at Buc-ee\'s', 'B4A', 'at most $110'),
   ('Eat a Food in Its Namesake Place', 'SCH', 'hamburger in Hamburg, 30 min from entering'),
   ('Eat the National / State Dish & Dessert', 'TAG/C4', ''),
   ('Eat an Egg', 'TAG/CTF', 'recognizably an egg'),
   ('Eat a Bug / Wagyu / a Snack on a Stick / Something Grape', 'CIRC/CTF/NZ', ''),
   ('Eat a McDonald\'s Item You Cannot Get in the US', 'CIRC', ''),
   ('Eat at a Michelin-Starred Restaurant / the Worst Restaurant', 'CIRC/TAG', ''),
   ('Have a Fast 3-Course Meal', 'TAG', 'three chains, three courses'),
   ('Eat an Import', 'TAGA', 'coins per 10 miles from where it was made'),
   ('Eat Spicy Food / Hot Chicken Trivia', 'C4/SS', ''),
   ('Run a Local Pastry Mile', 'CIRC', 'a pastry every quarter mile'),
   ('Eat a Carrot at the Carrot Park / Cheese at a Hot Spring / Cake Through a Straw', 'NZ', 'food at a themed place'),
   ('Drink a Blue Drink While Crossing Hokitika Gorge', 'NZ', ''),
   ('Complete a Cream Trip', 'NZ', 'eat cream on three islands'),
   ('Drink a Piña Colada in the Rain', 'B4A', ''),
   ('Take a Chevy to a Levee and Eat Pie', 'B4A', ''),
   ('Eat at In-N-Out / Cracker Barrel / Waffle House', 'B4A/ARC', ''),
   ('Visit a Diner, Drive-In or Dive', 'ARC', 'eat what Guy ate'),
   ('Have a Picnic on the Beach', 'ARC', 'three foods shared'),
   ('Purchase a Hat Worth More Than $100 / Wear a New Hat', 'CIRC/NZ', ''),
   ('Catch a Pokémon', 'CTF', 'buy anything with a Pokémon on it'),
   ('Get a Team Mascot', 'ARC', 'buy a stuffed animal, name it, keep it'),
   ('Sell Something from a Pawn Shop at a Pawn Shop', 'B4A', 'recover 50% in another state'),
   ('Mail Your Family a Regional Delicacy', 'ARC', ''),
   ('Get Drunk (many variants)', 'B4A/C4/CIRC/NZ/ARC', 'excluded for this game'),
  ]),
 ('body', 'Endurance & body', 'reps, distance, sweat',
  'Count-based physical tasks. We keep ours light.',
  'Ride the slides (Castro, McLaren, Bernal), summit climbs (Mt Davidson, Bernal Hill, Corona Heights).',
  [
   ('Do 100 Squats (for real)', 'TAG/CTF', ''),
   ('Complete 10 Obstacles on the MegaClimb', 'AU', ''),
   ('Ascend 500 Feet Without Touching Pavement', 'CIRC', ''),
   ('Travel 1 Mile Under Human Power', 'CIRC', 'on water'),
   ('Ride 3 Miles on Rollercoasters', 'CIRC', ''),
   ('Complete a ZORB Track / Go Extreme', 'NZ', ''),
   ('Go Skydiving / Bungee Jumping / Live Like You Were Dyin\'', 'B4A/CIRC/NZ/ARC', ''),
   ('Make a 30-Second Parkour Video', 'CIRC', ''),
   ('Be Fast and Furious', 'CTF', 'hit 20 mph under your own power while ranting'),
   ('Play Ice-Hand', 'SCH', 'squeeze an ice cube for seven minutes'),
   ('Keep Calm on The Drop at Dreamworld', 'AU', ''),
   ('Retrieve a Shell from 10 Feet Underwater', 'CIRC', ''),
   ('Catch a Fish (×4)', 'AU/CIRC/JPN/NZ', ''),
   ('Ride a Horse', 'ARC', 'five minutes'),
   ('Win a Game of Paintball', 'CIRC', ''),
   ('Pick Up Litter (×4)', 'B4A/CIRC/CTF/ARC', '5 pieces / 3 pounds / 3 quarter-sized pieces 10 ft apart / 10 pieces in a red sweater'),
  ]),
 ('perform', 'Performance & silliness', 'act, pose, sing, involve strangers',
  'The show\'s comedy engine. Most need an audience or a stranger, which is why Clipper Conquest mostly avoids them.',
  'Trio survivors: the Thinker freeze (Lincoln Park). Still lurking as alternates and due for the next pass: forced-perspective shots (USF spire, Potrero skyscraper, McLaren water tank, Bernal Bradford St) and pose cards (SoMa, Presidio nest, Nob Hill, Bayview murals, Treasure Island statue, Glen Park BART, Hayes Holy Rollers).',
  [
   ('High Five at the Highest Point', 'B4A', 'both airborne'),
   ('Make a Giant Roadside Object Look Small', 'ARC', 'forced perspective'),
   ('Become Totoro', 'CTF', 'umbrella at a bus stop, five minutes, smiling'),
   ('Go Super Saiyan', 'CTF', 'gel your hair straight up'),
   ('Become Florida Man', 'ARC', 'recreate a headline'),
   ('Get Knighted at an American Castle', 'ARC', ''),
   ('Wear Too Much Denim / Swap to a Tote', 'ARC/TAG', ''),
   ('Cry', 'ARC', 'real tears'),
   ('Busk Until You Earn One Dollar', 'C4', ''),
   ('Dance to the State Song / Run for Prime Minister', 'C4/NZ', ''),
   ('Praise the Ugliest Building / Criticize the Most Beautiful Place', 'B4A', ''),
   ('Respect the Weirdest Roadside Attraction', 'B4A', 'salute through the anthem'),
   ('Review a View / See a Great Wave', 'ARC/CTF', 'remark upon it'),
   ('Amuse a Moose / Explain the Birds and the Bees to a Bird', 'ARC', ''),
   ('Make a New Friend / a Penguin Friend (tell an animal your name)', 'NZ', '×2'),
   ('Get a Car to Honk', 'ARC', 'a sign must make a passing car honk'),
   ('Sing Classical Music', 'TAG2', 'hum a random classical piece until SoundHound recognizes it'),
   ('Fight Them on the Beaches', 'TAG2', 'menacing images from three kinds of place'),
   ('Give Your Partner a Genuine Compliment', 'NZ', ''),
   ('Take a Picture of the Mayor', 'B4A', ''),
   ('Get Recognized', 'JPN', 'a stranger must recognize you, unsolicited'),
   ('Ineffectively Advertise Jet Lag', 'B4A', 'one poster in the smallest town'),
   ('Create Content at That Wanaka Tree', 'NZ', 'coins per Reddit upvote'),
   ('Déjà Vu!', 'SCH', 'recreate a Jet Lag scene word-perfect where it was filmed'),
   ('Join the American Literary Canon', 'ARC', 'do what a novel\'s character does at the real spot'),
   ('Steal Elvis\' Spot', 'ARC', ''),
   ('Send an Anonymous Threat / Bribe the Chief of Police', 'TAG2/ARC', 'excluded'),
  ]),
 ('go', 'Go there, experience it', 'the place is the challenge',
  'Reach a specific kind of place, or get a specific experience. Works when the place is famous or remote.',
  'Coit Tower (North Beach), Lombard walk (Russian Hill), Mt Davidson cross, Sutro Baths tunnel, Lands End point, Fort Point (Presidio alt), '
  'Wave Organ (Marina).',
  [
   ('Go to the Grand Canyon', 'B4A', ''),
   ('Admire Tāne Mahuta', 'NZ', 'five minutes'),
   ('Take a Photo at Your City\'s Top 5 Landmarks', 'CIRC', 'transit only'),
   ('Visit the Top Attraction', 'TAG', 'five things you love about it'),
   ('Visit Any Museum / an Unpopular / an Obscure Museum', 'CIRC/C4/TAG/TAG2/CTF/ARC', 'share facts learned'),
   ('Use the Hundertwasser Toilets / a Fancy Restroom', 'NZ/TAG', ''),
   ('Eat Soup in a Helicopter', 'B4A', ''),
   ('Leave Your Prefecture by Boat / Get on a Boat', 'JPN/ARC', ''),
   ('Get on a Train Immediately', 'TAG', 'moving within 10 min'),
   ('Touch Both Oceans on the Same Day', 'B4A', ''),
   ('Touch Snow / Touch a Bird / Touch an Animal', 'CIRC/TAG', ''),
   ('Summit Mount Cleese', 'NZ', 'a renamed dump'),
   ('Visit One Castle Per Capita', 'SCH', 'two castles in an hour, with decrees'),
   ('Visit Every Spirit Halloween', 'B4A', ''),
   ('Attend a Local Event / Get a Pedicure', 'C4', ''),
   ('File a Geodetic Mark Recovery Form', 'B4A', ''),
   ('Spook Your Opponents', 'ARC', 'a reportedly haunted location'),
   ('Steal a Muffler Man\'s Identity', 'ARC', ''),
   ('Record an Iconic Sound', 'JPN', 'one of the 100 Soundscapes of Japan'),
  ]),
 ('trivia', 'Trivia, riddles, puzzles', 'quizzes and brain-teasers',
  'Quizzes written by the producers, plus a few pure logic puzzles. Clipper Conquest bans anything that depends on prior knowledge; a logic puzzle would be fine.',
  'None by design (removed: Presidio Terrace price guess, Palace of Fine Arts year, host-answer lines). Borderline: naming the MLK panel languages (SoMa) is sight-identification the host chose to keep.',
  [
   ('Pass Amy\'s Australian Slang Quiz / Questacon Quiz', 'AU', ''),
   ('Answer a Riddle Under a Big Bridge / Tristan\'s Riddle', 'JPN/TAG2/KOR/ARC', 'one guess'),
   ('Amy\'s Trivia Corner', 'TAG2', 'three questions, no penalty'),
   ('Amy\'s Puzzle Box', 'TAG2/TAGA', ''),
   ('Complete a Math Minute', 'NZ', 'a timed arithmetic sheet, zero mistakes'),
   ('Identify Monaco\'s Top Attractions', 'SCH', 'match anonymized reviews to sites'),
   ('Win Crayon Mastermind', 'TW', 'seven guesses at a crayon code (no knowledge needed — a pure logic puzzle)'),
   ('Finish a Puzzle / Solve a Newspaper Puzzle', 'AU/C4', 'jigsaw in 60 min; local paper\'s crossword'),
   ('Name the Other Doubly-Landlocked Country', 'SCH', 'five guesses'),
   ('Identify a President at a President\'s Birthplace', 'SS', 'from three inaugural sentences'),
   ('It\'s Five O\'Clock Somewhere', 'SS', 'name a city at each random time'),
   ('Identify K-Pop Groups', 'KOR', 'at every station'),
   ('Answer Hot Questions While Eating Hotter Chicken', 'SS', ''),
   ('Download the Riddle Faster Than the Wi-Fi', 'KOR', 'solve before the file finishes'),
   ('Commit an American Crime / Break a Law from Crime Spree', 'TAG/B4A', 'excluded'),
  ]),
 ('odd', 'One of a kind', 'doesn\'t fit anywhere, and that\'s the point',
  'Cards whose whole mechanic is their own premise. Fun on TV; hard to reuse. A Clipper Conquest challenge that lands here is a warning sign.',
  'None on purpose.',
  [
   ('Build a Giant Die', 'ARC', 'build a 1-ft die; the roll sets your flight distance'),
   ('Go Exactly One Mile', 'TAG', 'spin, point, go exactly a mile that way'),
   ('Go Somewhere #random', 'ARC', 'be #random for 15 min; a random 1–7 picks your airline'),
   ('Do 96 Things', 'SCH', 'burpees + half-ounces of wine + multiplication problems = 96'),
   ('Exercise Your Užupian Rights', 'SCH', 'three random constitutional rights become tasks'),
   ('Have a Good Time / 30 Minutes of Fun', 'CIRC/NZ', '2 hours; or 30 min at Megazone or a laundromat'),
   ('Dump One Ocean in Another Ocean', 'AU', ''),
   ('Destroy 5 Rings at 5 Volcanoes / Destroy One Ring', 'NZ', ''),
   ('Show a Plant the Garden City', 'NZ', 'four locations, ten minutes each'),
   ('Become a Pumpkin Parent', 'ARC', 'travel with a pumpkin for six hours'),
   ('Hide Your Phone and Leave', 'TAG', 'a quarter mile away'),
   ('Bury This Treasure / Bury a Treasure', 'TAGA/C4', 'three inches down, with a sign or coordinates'),
   ('Ship This Card / Burn This Card', 'B4A/TAG2', ''),
   ('Be Alone in the Xinying District', 'TW', 'film a teammate 1/8 mile away with no one else in frame'),
   ('Test the Honesty of the Australian People', 'AU', 'a $50 wallet must be taken within 10 min'),
   ('Trap a Bug in Vegemite / Toss a Tempting Meal', 'AU', 'make the local wildlife take the bait'),
   ('Fund the Military Industrial Complex', 'ARC', ''),
   ('Do the Damn Challenge', 'KOR', 'the card that explains nothing'),
   ('Become Johnny Appleseed / Smuggle Goods', 'ARC', '(no description on the wiki)'),
  ]),
 ('meta', 'Meta: curses, towers, steals', 'cards that act on the other team',
  'Not challenges — modifiers. Listed for completeness; Clipper Conquest has no card layer (yet).',
  'Nothing yet. If we ever add one: "opponents must walk sideways in this neighborhood" is the vibe.',
  [
   ('Japanorama curses (×10)', 'JPN', 'pickpocket, bounty hunter, toxic cloud, magic mirror…'),
   ('Race to the End of the World curses (×15)', 'NZ', 'walk backwards, no letter E, Element Song on repeat, RPS to advance'),
   ('Tag Across Europe curses (×3 + ×5 + ×3)', 'TAG/TAG2/TAGA', 'odd-numbered trains, knight moves, wet hat, Ratatouille\'d'),
   ('Snake Across South Korea curses (×4)', 'KOR', 'disembark, lock in your move, no effect'),
   ('Capture the Flag curses (×5) and towers (×9)', 'CTF', 'late train, Japanese phone, Hello Kitty, melon; Gravity/Ice/Jail/Lightning/Mud/Odd/Pizza/Trap/Vampire towers'),
   ('Taiwan "(Steal)" cards', 'TW', 'a failed challenge can be stolen and completed by the other team'),
  ]),
]

def esc(s): return html.escape(s)

# corpus count for the header
corpus = (HERE / 'JETLAG_EXAMPLES.md').read_text()
n_corpus = len(re.findall(r'^- \*\*', corpus, re.M))
seasons = re.findall(r'^## (.+?) \(\d+\)', corpus, re.M)

nav = ''.join(f'<a href="#{k}">{esc(t)}<span>{len(items)}</span></a>'
              for k, t, _, _, _, items in CATS)

sections = []
for k, title, sub, blurb, ours, items in CATS:
    rows = ''.join(
        f'<li><span class="t">{esc(t)}</span><span class="s">{esc(se)}</span>'
        + (f'<span class="g">{esc(g)}</span>' if g else '') + '</li>'
        for t, se, g in items)
    sections.append(f'''
<section id="{k}">
  <header>
    <p class="eyebrow">{esc(sub)}</p>
    <h2>{esc(title)} <span class="count">{len(items)}</span></h2>
    <p class="blurb">{esc(blurb)}</p>
    <p class="ours"><b>In Clipper Conquest:</b> {esc(ours)}</p>
  </header>
  <ul class="items">{rows}</ul>
</section>''')

legend = ''.join(f'<span><b>{k}</b> {esc(v)}</span>' for k, v in S.items())

page = f'''<title>Jet Lag Mechanics</title>
<meta name="description" content="Every Jet Lag: The Game challenge sorted by mechanic, with notes on what Clipper Conquest borrows.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;1,400&display=swap">
<style>
:root {{
  --ground:#eef1f5; --surface:#ffffff; --ink:#111827; --muted:#5b6474; --line:#d5dbe4;
  --accent:#e4572e; --accent-ink:#ffffff; --route:#2d6a9f; --chip:#e3e8ef;
  --display:"Barlow Condensed","Arial Narrow",Impact,sans-serif;
  --body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  color-scheme:dark; --ground:#0f1520; --surface:#182130; --ink:#e6ebf2; --muted:#98a3b5; --line:#2a3546;
  --accent:#ff7a4d; --accent-ink:#0f1520; --route:#7fb3e0; --chip:#233043; }} }}
:root[data-theme="dark"] {{
  color-scheme:dark; --ground:#0f1520; --surface:#182130; --ink:#e6ebf2; --muted:#98a3b5; --line:#2a3546;
  --accent:#ff7a4d; --accent-ink:#0f1520; --route:#7fb3e0; --chip:#233043; }}
* {{ box-sizing:border-box; }}
body {{ background:var(--ground); color:var(--ink); font-family:var(--body); font-size:15px; line-height:1.5;
  padding-inline:16px; padding-block:0 48px; }}
.wrap {{ max-width:760px; margin:0 auto; }}
h1 {{ font-family:var(--display); font-weight:700; font-size:clamp(40px,9vw,64px); line-height:.95; letter-spacing:.01em;
  text-transform:uppercase; margin:28px 0 6px; text-wrap:balance; }}
h1 em {{ font-style:normal; color:var(--accent); }}
.lede {{ color:var(--muted); max-width:60ch; margin:0 0 6px; }}
.stats {{ display:flex; flex-wrap:wrap; gap:6px 18px; font-family:var(--display); font-size:18px; text-transform:uppercase;
  letter-spacing:.04em; color:var(--muted); margin:0 0 18px; font-variant-numeric:tabular-nums; }}
.stats b {{ color:var(--ink); font-weight:700; }}
nav {{ position:sticky; top:env(safe-area-inset-top,0px); z-index:5; background:var(--ground); padding:8px 0; margin:0 -16px; padding-inline:16px;
  border-bottom:1px solid var(--line); }}
nav .row {{ display:flex; gap:6px; overflow-x:auto; scrollbar-width:none; padding-bottom:2px; }}
nav .row::-webkit-scrollbar {{ display:none; }}
nav a {{ flex:0 0 auto; display:inline-flex; align-items:center; gap:6px; background:var(--chip); color:var(--ink); text-decoration:none;
  font-family:var(--display); font-size:15px; text-transform:uppercase; letter-spacing:.04em; padding:5px 10px; border-radius:999px; }}
nav a span {{ font-size:12px; color:var(--muted); font-variant-numeric:tabular-nums; }}
nav a:focus-visible, .search input:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
.search {{ margin:14px 0 6px; }}
.search input {{ width:100%; font:inherit; font-size:16px; padding:10px 12px; border:1px solid var(--line); border-radius:8px;
  background:var(--surface); color:var(--ink); }}
.search p {{ margin:4px 2px 0; font-size:13px; color:var(--muted); font-variant-numeric:tabular-nums; }}
section {{ margin-top:30px; scroll-margin-top:70px; }}
section header {{ border-top:3px solid var(--ink); padding-top:10px; }}
.eyebrow {{ margin:0; font-size:12px; text-transform:uppercase; letter-spacing:.12em; color:var(--accent); font-weight:500; }}
h2 {{ font-family:var(--display); font-weight:700; font-size:32px; line-height:1; margin:4px 0 8px; text-transform:uppercase; letter-spacing:.01em;
  display:flex; align-items:baseline; gap:10px; }}
h2 .count {{ font-size:18px; color:var(--muted); font-variant-numeric:tabular-nums; }}
.blurb {{ margin:0 0 8px; max-width:62ch; }}
.ours {{ margin:0 0 10px; font-size:14px; color:var(--muted); max-width:70ch; border-left:3px solid var(--route); padding-left:10px; }}
.ours b {{ color:var(--route); font-weight:500; }}
ul.items {{ list-style:none; margin:0; padding:0; background:var(--surface); border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
ul.items li {{ display:grid; grid-template-columns:minmax(0,1fr) auto; grid-template-areas:"t s" "g g"; gap:0 10px; padding:8px 12px;
  border-top:1px solid var(--line); }}
ul.items li:first-child {{ border-top:0; }}
ul.items li[hidden] {{ display:none; }}
.t {{ grid-area:t; font-weight:500; }}
.s {{ grid-area:s; font-family:var(--display); font-size:13px; letter-spacing:.06em; color:var(--muted); align-self:start; padding-top:3px; }}
.g {{ grid-area:g; color:var(--muted); font-size:14px; }}
.legend {{ display:flex; flex-wrap:wrap; gap:4px 14px; font-size:12px; color:var(--muted); margin:14px 0 0; }}
.legend b {{ font-family:var(--display); font-size:13px; letter-spacing:.06em; color:var(--ink); font-weight:600; }}
.foot {{ margin-top:36px; font-size:13px; color:var(--muted); border-top:1px solid var(--line); padding-top:12px; max-width:70ch; }}
@media (prefers-reduced-motion:no-preference) {{ html {{ scroll-behavior:smooth; }} }}
</style>
<div class="wrap">
  <h1>Jet Lag <em>mechanics</em></h1>
  <p class="lede">Every challenge from the Jet Lag: The Game wiki, sorted into the families of game underneath them. Each family notes what Clipper Conquest already borrows from it.</p>
  <p class="stats"><span><b>{n_corpus}</b> cards scraped</span><span><b>{len(seasons)}</b> seasons</span><span><b>{len(CATS)}</b> families</span></p>
  <nav><div class="row">{nav}</div></nav>
  <div class="search"><input id="q" type="search" placeholder="Filter challenges… (e.g. blindfold, bottle, memorize)" autocomplete="off"><p id="qn"></p></div>
  {''.join(sections)}
  <p class="legend">{legend}</p>
  <p class="foot">A card appears in more than one family when it genuinely mixes mechanics (a jellyfish census is both an estimate and a mind meld). Curses, towers and steals are summarized, not listed one by one. Source: challenges/JETLAG_EXAMPLES.md, scraped from jetlag.fandom.com.</p>
</div>
<script>
(function(){{
  var q=document.getElementById('q'), qn=document.getElementById('qn');
  var lis=[].slice.call(document.querySelectorAll('ul.items li'));
  var secs=[].slice.call(document.querySelectorAll('section'));
  try {{ var saved=localStorage.getItem('jl-q'); if(saved) q.value=saved; }} catch(e) {{}}
  function run(){{
    var v=q.value.trim().toLowerCase(); var n=0;
    lis.forEach(function(li){{ var txt=(li.querySelector('.t').textContent+' '+(li.querySelector('.g')||{{textContent:''}}).textContent).toLowerCase(); var hit=!v||txt.indexOf(v)>=0; li.hidden=!hit; if(hit) n++; }});
    secs.forEach(function(s){{ var empty=!s.querySelector('li:not([hidden])'); s.hidden=empty; var a=document.querySelector('nav a[href="#'+s.id+'"]'); if(a) a.hidden=empty; }});
    qn.textContent=v?(n+' matching'):'';
    try {{ localStorage.setItem('jl-q', q.value); }} catch(e) {{}}
  }}
  q.addEventListener('input', run); run();
}})();
</script>
'''
out = HERE / 'jetlag_categories.html'
out.write_text(page)
print(f'{out.name}: {out.stat().st_size//1024} KB, {sum(len(c[5]) for c in CATS)} rows in {len(CATS)} families; corpus {n_corpus} cards, {len(seasons)} seasons')
