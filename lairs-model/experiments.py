"""Strategy experiments. Run:  python experiments.py [dice|explorer|race|lairs|all] [--quick]"""
import random
import sys
from dataclasses import replace
from statistics import mean

from lairs.bots import HeuristicBot, Params
from lairs.dice import dist, kill_plan, p_success
from lairs.lair import random_lair
from lairs.optimize import hill_climb, slowness
from lairs.sim import lair_pairs, match, solo_stats

QUICK = "--quick" in sys.argv
BASE = Params()

VARIANTS = {
    "explore=creep": dict(explore="creep"),
    "explore=peer": dict(explore="peer"),
    "no Perception-peer": dict(use_p_peer=False),
    "fight=never": dict(fight="never"),
    "fight with 2 dice (p>=.35)": dict(fight_p=0.35),
    "fight with 4 dice (p>=.95)": dict(fight_p=0.95),
    "whittle": dict(whittle=True),
    "leave rather than wait": dict(wait_to_fight=False),
    "disarm with 3 dice (p>=.9)": dict(disarm_p=0.9),
    "never disarm (eat traps)": dict(disarm_p=1.1),
    "disarm stumbled traps": dict(disarm_stumbled=True),
    "exit after 3 chests": dict(exit_when="chests"),
    "exit after everything": dict(exit_when="all"),
    "no conserve": dict(conserve=False),
}


def dice():
    print("== Dice (faces 1,2,2,3,3,4; mean 2.5) ==")
    print("P(success)   " + "".join(f"{n} dice  " for n in range(1, 6)))
    for t in (2, 3, 4, 5, 6):
        print(f"target {t}:    " + "".join(f"{p_success(n, t):5.0%}   " for n in range(1, 6)))
    print("\nCheapest way to kill a Blob (target 6), cost in cubes, damage persists:")
    for fc in (1, 2, 3, 4):
        V = kill_plan(6, fc)
        plan = ", ".join(f"T{t}:{V[t][1]}d" for t in range(6, 0, -1))
        print(f"  a failed fight costs {fc} cubes -> expect {V[6][0]:.2f} cubes; dice by target: {plan}")


def explorer():
    n = 60 if QUICK else 400
    pairs = lair_pairs(n, seed=11)
    lairs = [l for pair in pairs for l in pair]
    base = HeuristicBot(BASE)
    print(f"\n== Explorer knobs: each variant vs the baseline bot, {4 * n} games on random legal lairs ==")
    print(f"baseline = {BASE}")
    s = solo_stats(base, lairs)
    print(f"baseline solo: {s['turns']:.2f} turns to exit, {s['strikes']:.2f} strikes taken\n")
    print(f"{'variant':30s} {'win%':>6s} {'draw%':>6s} {'VP':>6s} {'oppVP':>6s} {'1st out':>8s} {'solo turns':>11s} {'strikes':>8s}")
    for label, kw in VARIANTS.items():
        bot = HeuristicBot(replace(BASE, **kw))
        m = match(bot, base, pairs)
        s = solo_stats(bot, lairs)
        print(f"{label:30s} {m['win']:6.1%} {m['draw']:6.1%} {m['score']:6.2f} {m['opp_score']:6.2f} "
              f"{m['first_exit']:8.1%} {s['turns']:11.2f} {s['strikes']:8.2f}")
    print("(win% above 50 means the variant beats the baseline; +-2.5 points is noise)")


def race():
    from lairs.game import Game
    n = 100 if QUICK else 600
    bot = HeuristicBot(BASE)
    out_first = went_first = games = 0
    turns, margin, both = [], [], 0
    for k, (la, lb) in enumerate(lair_pairs(n, seed=23)):
        for first in (0, 1):
            r = Game([la, lb], [bot, bot], seed=k * 2 + first, first=first).play()
            games += 1
            leaver = r.exit_rank.index(1)
            out_first += r.winner == leaver
            went_first += r.winner == first
            both += None not in r.exit_rank
            turns.append(r.turns[leaver])
            margin.append(abs(r.scores[0] - r.scores[1]))
    print(f"\n== The race (baseline bot vs itself, {games} games) ==")
    print(f"first player to exit wins {out_first / games:.1%}; the other player also gets out {both / games:.1%} of the time")
    print(f"player who takes the first turn wins {went_first / games:.1%}")
    print(f"game ends on turn {mean(turns):.1f} on average; mean winning margin {mean(margin):.1f} VP")


def lairs():
    print("\n== Lair building ==")
    rng = random.Random(3)
    bots = [HeuristicBot(BASE), HeuristicBot(replace(BASE, explore="peer"))]
    sample = [random_lair(rng) for _ in range(40 if QUICK else 150)]
    sl = sorted((slowness(l, bots, 10), k) for k, l in enumerate(sample))
    print(f"random legal lairs: turns-to-exit min {sl[0][0]:.1f} / median {sl[len(sl) // 2][0]:.1f} / max {sl[-1][0]:.1f}")
    for walls in (17, 20):
        ls = [random_lair(rng, walls) for _ in range(40 if QUICK else 150)]
        print(f"  {walls} walls: mean {mean(slowness(l, bots, 6) for l in ls):.2f} turns")
    best, score = hill_climb(bots, iters=60 if QUICK else 500, seeds=12, seed=5, start=sample[sl[-1][1]])
    fresh = slowness(best, bots, 60)
    print(f"\nhill-climbed lair: {fresh:.1f} turns on fresh dice (training score {score:.1f})")
    print(best)
    ref = [(random_lair(rng), best) for _ in range(30 if QUICK else 150)]
    # player 0 built `best` (index 1 of the pair is explored by player 0, so swap roles by hand)
    a = HeuristicBot(BASE)
    from lairs.game import Game
    w = d = n = 0
    for k, (rnd, opt) in enumerate(ref):
        for first in (0, 1):
            r = Game([opt, rnd], [a, a], seed=k * 2 + first, first=first).play()  # player 0 built opt
            n += 1
            w += r.winner == 0
            d += r.winner is None
    print(f"builder of the tuned lair vs builders of random lairs (same explorer bot): wins {w / n:.1%}, draws {d / n:.1%}")
    return best


if __name__ == "__main__":
    what = next((a for a in sys.argv[1:] if not a.startswith("--")), "all")
    if what in ("dice", "all"):
        dice()
    if what in ("explorer", "all"):
        explorer()
    if what in ("race", "all"):
        race()
    if what in ("lairs", "all"):
        lairs()
