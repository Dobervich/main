"""Exact maths for the Lairs dice (faces 1,2,2,3,3,4)."""
from functools import lru_cache

FACES = (1, 2, 2, 3, 3, 4)
BLOB_TARGET = 6
PIT_TARGET = 5


@lru_cache(maxsize=None)
def dist(n):
    """Probability distribution of the total of n dice, as {total: prob}."""
    d = {0: 1.0}
    for _ in range(n):
        nd = {}
        for t, p in d.items():
            for f in FACES:
                nd[t + f] = nd.get(t + f, 0.0) + p / 6
        d = nd
    return d


@lru_cache(maxsize=None)
def p_success(n, target):
    return sum(p for t, p in dist(n).items() if t >= target)


@lru_cache(maxsize=None)
def dice_needed(target, min_p, max_n=12):
    """Fewest dice whose success chance is at least min_p."""
    for n in range(1, max_n + 1):
        if p_success(n, target) >= min_p:
            return n
    return max_n


def kill_plan(target=BLOB_TARGET, fail_cost=2.0, max_n=6):
    """Cheapest way to kill a monster when damage persists between attempts.

    Cost is counted in cubes: one per die, plus fail_cost per failed check
    (a Blob strike fatigues two cubes; how much that hurts depends on which
    cubes you can feed it). Returns {target: (expected_cost, best_dice)}.
    """
    V = {}
    for t in range(1, target + 1):
        best = None
        for n in range(1, max_n + 1):
            c = float(n)
            for s, p in dist(n).items():
                if s < t:
                    c += p * (fail_cost + V[t - s][0])
            if best is None or c < best[0] - 1e-12:
                best = (c, n)
        V[t] = best
    return V
