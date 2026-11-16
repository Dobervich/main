# Lairs strategy model

A simulation of the **Lairs** base game (KTBG) for exploring strategy: a rules
engine, parameterised explorer bots, a lair generator/legality checker, and a
lair optimiser. Pure Python, no dependencies (pytest for the tests).

```
python experiments.py            # all experiments (~3 min); add --quick for a fast pass
python experiments.py explorer   # or: dice | race | lairs
python lair_study.py             # what makes a lair hard (~2 min)
python -m pytest -q tests
```

## Layout

| file | what it is |
|---|---|
| `lairs/dice.py` | exact odds for the 1-2-2-3-3-4 dice; cheapest Blob-kill plan |
| `lairs/lair.py` | 6x6 board, walls, features, the three building rules, text format, random legal lairs |
| `lairs/game.py` | full turn engine: cubes (fresh/spent/fatigued/conserved), Creep, Hustle, Backtrack, Peer, Conserve, checks, strikes, chests, exit, scoring |
| `lairs/treasures.py` | treasure cards and best-four scoring |
| `lairs/bots.py` | `HeuristicBot`; every field of `Params` is a strategy knob |
| `lairs/sim.py` | solo runs and head-to-head matches |
| `lairs/optimize.py` | hill-climbs a lair to slow explorers down |

Bots only see an `Obs`, which refuses to reveal Unknown spaces.

## Assumptions to know about

- **The treasure deck is a placeholder.** The rulebook doesn't list the 22
  cards. The six shown in its examples are modelled; the other sixteen are
  invented in the same style. Treasure VP are therefore approximate. Replace
  `DECK` in `lairs/treasures.py` with the real cards.
- Entering a **Known** hazard forces an immediate check (zero dice allowed).
  Flag: `Rules.known_entry_forces_check`.
- In a hazard space you may not Peer or Conserve (neither moves you out).
- A Conserved attribute cube counts as that attribute on both of its spends.
- Strike penalties are paid with the least painful cubes automatically
  (Spent before Fresh before Conserved, white before coloured).
- "Locate" never happens in the base game, so it isn't modelled.

## Findings

Bots playing random legal lairs unless stated. Win rates are against the
baseline bot (Hustle to explore, hunt Blobs with 3 dice, leave as soon as
allowed); about +-2.5 points is noise.

**Dice.** Blob (6): 2 dice 36%, 3 dice 88%, 4 dice 99%. Pit (5): 2 dice 64%,
3 dice 97%. Three dice at a fresh Blob is the cheapest kill however much a
failed fight is assumed to cost.

**It is a race.** In mirror matches the first player out wins 84% of games,
and whoever takes the first turn wins 57%. Games end around turn 6-7.

| explorer change | win% vs baseline | solo turns to exit |
|---|---|---|
| baseline | 50 | 7.7 |
| Peer into every unknown space | 28 | 9.5 |
| Creep instead of Hustle | 43 | 8.1 |
| don't use the Perception cube to Peer | 45 | 8.2 |
| avoid Blobs unless required | 41 | 8.7 |
| 2 dice at a Blob | 48 | 7.8 |
| 4 dice at a Blob | 43 | 8.2 |
| walk away from a Blob instead of waiting a turn | 44 | 8.1 |
| stop to disarm a trap you fell into | 44 | 8.2 |
| stay until all 3 chests are open | 43 | 9.5 |
| stay for 3 chests and 3 Blobs | 38 | 10.8 |
| attack under-strength to bank damage; trap dice 0 vs 2 vs 3; Conserve leftovers | 48-50 | ~7.7 |

## Lair design (`lair_study.py`)

1200 random legal lairs: explorers need 8.6 turns on average to get out
(sd 1.2; 10th percentile 7.0, 90th 10.2). Wall count (17 vs 20) is irrelevant.
What correlates with a slow lair:

| feature | corr. with turns | effect |
|---|---|---|
| chests far from the exit | +0.46 | closest quarter 7.7 turns, farthest quarter 9.3 |
| exit is a dead end (one way in) | +0.35 | 8.3 -> 9.4 |
| hazards you must cross to reach the exit | +0.29 | none 8.3, one 8.9, two 9.4 |
| chests far from the start / behind a hazard | +0.16 | about +0.5 turn |
| start far from the exit | +0.15 | about +0.3 turn |
| hazards near the start or exit, number of dead ends, Blob (vs Pit) on the exit route | ~0 | none |

Random lairs that tick the first three boxes average 9.9 turns and their
builder wins about 55%. Searched lairs do much better: eight independent
hill-climbs reached 11.6-13.6 turns, and their builders beat random-lair
builders 71-90% of the time with the baseline explorer, and 50-92% with three
explorer styles the search never saw. Seven of the eight have a dead-end exit
and all eight put at least one hazard on every route to it; chests average
9.5 steps from the exit (random: 5.8). The two most robust:

```
+---+---+---+---+---+---+     +---+---+---+---+---+---+
| . | .   M   . | C   T |     | E | . | .   .   .   . |
+   +   +   +   +---+   +     +   +   +   +   +---+   +
| .   .   .   .   .   . |     | . | . | C | .   .   M |
+   +---+---+   +---+---+     +   +   +---+---+---+   +
| .   . | . | .   M   . |     | . | .   .   S   .   T |
+   +   +   +   +---+---+     +   +---+---+   +   +   +
| .   T | T   .   S   . |     | T   .   . | .   . | . |
+   +   +---+---+---+   +     +   +---+   +   +   +   +
| C | .   .   . | C   M |     | .   .   M   .   C | M |
+---+   +   +   +---+   +     +---+---+   +   +---+   +
| .   .   .   E | .   . |     | .   .   .   T   . | C |
+---+---+---+---+---+---+     +---+---+---+---+---+---+
 79-88% across four bots       78-89% across four bots
```

Caveat: these are tuned against heuristic bots that explore the nearest
unknown space. A human who expects "exit at the end of a guarded corridor,
far from the loot" will do better than the bots did.
