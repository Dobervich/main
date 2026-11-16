"""What makes a lair hard? Run:  python lair_study.py [stats|search|all] [--quick]

stats  : structural features of random legal lairs vs how long explorers take
search : several independent hill-climbs, each validated on fresh dice
"""
import heapq
import random
import sys
from collections import deque
from dataclasses import replace
from multiprocessing import Pool
from statistics import mean, pstdev

from lairs.bots import HeuristicBot, Params
from lairs.game import Game
from lairs.lair import CELLS, CHEST, EXIT, MONSTER, TRAP, random_lair
from lairs.optimize import hill_climb, slowness

QUICK = "--quick" in sys.argv
BASE = Params()
TRAIN = [HeuristicBot(BASE), HeuristicBot(replace(BASE, explore="peer"))]
# explorers the search never saw, to check a design is not just exploiting one bot
UNSEEN = {
    "creeper": HeuristicBot(replace(BASE, explore="creep")),
    "blob-avoider": HeuristicBot(replace(BASE, fight="never")),
    "loot-all-chests": HeuristicBot(replace(BASE, exit_when="chests")),
}


def _dist(lair, src, cost=lambda f: 1):
    d = {src: 0}
    pq = [(0, src)]
    while pq:
        x, u = heapq.heappop(pq)
        if x > d[u]:
            continue
        for _, v in lair.open_dirs(u):
            nx = x + cost(lair.features.get(v))
            if nx < d.get(v, 1e9):
                d[v] = nx
                heapq.heappush(pq, (nx, v))
    return d


def features(lair):
    s, e = lair.start, lair.cells_with(EXIT)[0]
    chests = lair.cells_with(CHEST)
    steps = _dist(lair, s)
    guards = _dist(lair, s, lambda f: f in (MONSTER, TRAP))   # fewest hazards you must cross
    blobs = _dist(lair, s, lambda f: f == MONSTER)
    from_exit = _dist(lair, e)
    hazards = lair.cells_with(MONSTER) + lair.cells_with(TRAP)
    return {
        "start->exit steps": steps[e],
        "hazards guarding exit": guards[e],
        "Blobs guarding exit": blobs[e],
        "exit is a dead end": int(len(lair.open_dirs(e)) == 1),
        "mean start->chest steps": mean(steps[c] for c in chests),
        "chests behind a hazard": sum(guards[c] > 0 for c in chests),
        "mean chest->exit steps": mean(from_exit[c] for c in chests),
        "hazards within 2 of start": sum(steps[h] <= 2 for h in hazards),
        "hazards within 2 of exit": sum(from_exit[h] <= 2 for h in hazards),
        "dead-end spaces": sum(len(lair.open_dirs(c)) == 1 for c in CELLS),
        "farthest space from start": max(steps.values()),
    }


def corr(xs, ys):
    sx, sy = pstdev(xs), pstdev(ys)
    if not sx or not sy:
        return 0.0
    mx, my = mean(xs), mean(ys)
    return mean((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def builder_winrate(lair, bot, n, seed=0):
    """Win rate of the lair's builder when both players use `bot` and the rival builds at random."""
    rng = random.Random(seed)
    w = 0
    for k in range(n):
        rnd = random_lair(rng)
        for first in (0, 1):
            w += Game([lair, rnd], [bot, bot], seed=seed + 2 * k + first, first=first).play().winner == 0
    return w / (2 * n)


def _score(lair):
    return slowness(lair, TRAIN, 8), features(lair)


def stats(pool):
    n = 150 if QUICK else 1200
    rng = random.Random(101)
    lairs = [random_lair(rng) for _ in range(n)]
    rows = pool.map(_score, lairs)
    turns = [r[0] for r in rows]
    print(f"== {n} random legal lairs: turns the explorers need to get out ==")
    q = sorted(turns)
    print(f"mean {mean(turns):.2f}, sd {pstdev(turns):.2f}, 10th pct {q[n // 10]:.1f}, median {q[n // 2]:.1f}, 90th pct {q[9 * n // 10]:.1f}\n")
    print(f"{'feature':28s} {'corr':>6s}   mean turns by feature value (n lairs)")
    for name in rows[0][1]:
        xs = [r[1][name] for r in rows]
        vals = sorted(set(xs))
        if len(vals) > 5:  # bucket continuous features into quartiles
            cut = [sorted(xs)[k * n // 4] for k in (1, 2, 3)]
            grp = lambda x: sum(x >= c for c in cut)
            label = ["lowest quarter", "2nd", "3rd", "highest quarter"]
            keys = range(4)
        else:
            grp, label, keys = (lambda x: x), {v: str(v) for v in vals}, vals
        parts = []
        for k in keys:
            ts = [t for x, t in zip(xs, turns) if grp(x) == k]
            if ts:
                parts.append(f"{label[k]}: {mean(ts):.1f} ({len(ts)})")
        print(f"{name:28s} {corr(xs, turns):+6.2f}   " + " | ".join(parts))
    return lairs, turns


def _climb(seed):
    return hill_climb(TRAIN, iters=60 if QUICK else 450, seeds=10, seed=seed)[0]


def _validate(lair):
    n = 25 if QUICK else 150
    out = {"turns": slowness(lair, TRAIN, 40), "baseline": builder_winrate(lair, TRAIN[0], n, seed=9000)}
    for name, bot in UNSEEN.items():
        out[name] = builder_winrate(lair, bot, n, seed=9000)
    return out


def search(pool):
    runs = 4 if QUICK else 8
    print(f"\n== {runs} independent hill-climbs (objective: turns to escape for the hustle and peer bots) ==")
    found = pool.map(_climb, range(200, 200 + runs))
    checks = pool.map(_validate, found)
    order = sorted(range(runs), key=lambda k: -mean(v for n, v in checks[k].items() if n != "turns"))
    cols = ["baseline"] + list(UNSEEN)
    print("builder win rate vs a random-lair builder, by which explorer bot both players use (fresh dice):")
    print(f"{'lair':>4s} {'turns':>6s} " + " ".join(f"{c:>16s}" for c in cols))
    for rank, k in enumerate(order):
        c = checks[k]
        print(f"{'#' + str(rank + 1):>4s} {c['turns']:6.1f} " + " ".join(f"{c[x]:16.0%}" for x in cols))
    feats = [features(found[k]) for k in order]
    print("\nstructure of the found lairs (same order):")
    for name in feats[0]:
        print(f"  {name:28s} " + " ".join(f"{f[name]:5.1f}" for f in feats))
    for rank, k in enumerate(order[:3]):
        print(f"\nlair #{rank + 1}\n{found[k]}")


if __name__ == "__main__":
    what = next((a for a in sys.argv[1:] if not a.startswith("--")), "all")
    with Pool() as pool:
        if what in ("stats", "all"):
            stats(pool)
        if what in ("search", "all"):
            search(pool)
