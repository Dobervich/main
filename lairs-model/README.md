# Lairs strategy model

A simulation of the **Lairs** base game (KTBG) for exploring strategy: a rules
engine, parameterised explorer bots, a lair generator/legality checker, and a
lair optimiser. Pure Python, no dependencies (pytest for the tests).

```
python experiments.py            # all experiments (~3 min); add --quick for a fast pass
python experiments.py explorer   # or: dice | race | lairs
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

## First findings

All from `experiments.py`, bots playing random legal lairs unless stated.
Win rates are against the baseline bot (Hustle to explore, hunt Blobs with
3 dice, leave as soon as allowed); about +-2.5 points is noise.

**Dice.** Blob (6): 2 dice 36%, 3 dice 88%, 4 dice 99%. Pit (5): 2 dice 64%,
3 dice 97%. Three dice at a fresh Blob is the cheapest kill however much a
failed fight is assumed to cost.

**It is a race.** In mirror matches the first player out wins 82% of games,
and whoever takes the first turn wins 57%. Games end around turn 6-7.

| explorer change | win% vs baseline | solo turns to exit |
|---|---|---|
| baseline | 50 | 7.8 |
| Peer into every unknown space | 28 | 9.4 |
| Creep instead of Hustle | 45 | 8.2 |
| don't use the Perception cube to Peer | 44 | 8.3 |
| avoid Blobs unless required | 44 | 8.7 |
| 2 dice at a Blob | 49 | 7.9 |
| 4 dice at a Blob | 43 | 8.3 |
| walk away from a Blob instead of waiting a turn | 44 | 8.2 |
| stop to disarm a trap you fell into | 45 | 8.2 |
| stay until all 3 chests are open | 46 | 9.4 |
| stay for 3 chests and 3 Blobs | 41 | 10.6 |
| attack under-strength to bank damage; trap dice 0 vs 2 vs 3; Conserve leftovers | 49-51 | ~7.8 |

- Careful play loses. The Peer-everything bot takes 0.6 strikes a game
  against 4.2 for the Hustler, and still wins only 28%.
- The one cheap Peer (Perception cube) is worth using every turn.
- Staying for more loot does raise VP (about +1.5) but hands the opponent the
  4 VP exit bonus and the tiebreak more often than it pays.

**Lair building matters more than exploring.** Random legal lairs take the
bots anywhere from 4.5 to 12.5 turns to escape (median 8.2); 17 vs 20 walls
barely moves the average. A hill-climbed lair holds them for 15.7 turns and
its builder wins 82% against builders of random lairs:

```
+---+---+---+---+---+---+
| S   .   .   .   . | . |
+---+   +   +   +---+   +
| .   . | .   C | . | T |
+---+---+   +   +   +   +
| .   .   .   M   M   T |
+   +   +---+---+   +---+
| . | C   . | .   M   . |
+   +   +   +---+   +   +
| . | .   .   . | . | E |
+   +   +   +   +   +   +
| C | .   . | .   T | . |
+---+---+---+---+---+---+
```

The exit sits in a pocket whose only door is a Blob, all three Blobs are
stacked around that door, and the chests are on the far side of the board.
This lair was tuned against these bots, so treat 82% as an upper bound: a
human who guesses the pattern would do better.
