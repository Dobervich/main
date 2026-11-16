"""Lair-building search: hill-climb a lair to slow down a set of explorer bots."""
import random
from statistics import mean

from .lair import ALL_EDGES, CELLS, Lair, random_lair
from .sim import solo


def mutate(lair, rng):
    """A random small legal change: move a wall, move a feature, or swap two features."""
    for _ in range(200):
        walls, feats = set(lair.walls), dict(lair.features)
        kind = rng.random()
        if kind < 0.5:
            walls.remove(rng.choice(sorted(walls)))
            walls.add(rng.choice([e for e in ALL_EDGES if e not in walls]))
        elif kind < 0.8:
            src = rng.choice(sorted(feats))
            dst = rng.choice([c for c in CELLS if c not in feats])
            feats[dst] = feats.pop(src)
        else:
            a, b = rng.sample(sorted(feats), 2)
            feats[a], feats[b] = feats[b], feats[a]
        new = Lair(walls, feats)
        if new.is_legal():
            return new
    return lair


def slowness(lair, bots, seeds=20):
    """Mean number of turns the bots need to get out (higher = nastier lair)."""
    return mean(solo(lair, b, seed=s)[0] for b in bots for s in range(seeds))


def hill_climb(bots, iters=300, seeds=20, seed=0, start=None, verbose=False):
    rng = random.Random(seed)
    best = start or random_lair(rng)
    score = slowness(best, bots, seeds)
    for k in range(iters):
        cand = mutate(best, rng)
        s = slowness(cand, bots, seeds)
        if s >= score:
            if verbose and s > score:
                print(f"  iter {k}: {score:.2f} -> {s:.2f}")
            best, score = cand, s
    return best, score
