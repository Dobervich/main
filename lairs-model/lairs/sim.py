"""Running many games and summarising them."""
import random
from statistics import mean

from .bots import HeuristicBot, PassBot
from .game import Game, Rules
from .lair import random_lair


def solo(lair, bot, seed=0, max_turns=40):
    """One explorer alone in a lair. Returns (turns until exit or max_turns, Result)."""
    g = Game([lair, lair], [PassBot(), bot], seed=seed, first=1, rules=Rules(max_turns=max_turns))
    p = g.players[1]
    while not p.exited and p.turns < max_turns:
        g.take_turn(1)
    return p.turns, g.result()


def solo_stats(bot, lairs, seeds=1):
    turns, strikes, chests, monsters = [], [], [], []
    for k, lair in enumerate(lairs):
        for s in range(seeds):
            t, r = solo(lair, bot, seed=1000 * k + s)
            turns.append(t)
            strikes.append(r.strikes[1])
            chests.append(r.chests[1])
            monsters.append(r.monsters[1])
    return {"turns": mean(turns), "strikes": mean(strikes), "chests": mean(chests), "monsters": mean(monsters)}


def match(bot_a, bot_b, lair_pairs, seed=0):
    """Each lair pair is played twice with sides swapped. Returns bot_a's summary."""
    wins = draws = n = 0
    sa, sb, first_exit = [], [], 0
    for k, (la, lb) in enumerate(lair_pairs):
        for swap in (0, 1):
            # bot_a explores lb, bot_b explores la (then the lairs are swapped)
            lairs = [la, lb] if not swap else [lb, la]
            for first in (0, 1):
                r = Game(lairs, [bot_a, bot_b], seed=seed + 7919 * k + 2 * swap + first, first=first).play()
                n += 1
                wins += r.winner == 0
                draws += r.winner is None
                sa.append(r.scores[0])
                sb.append(r.scores[1])
                first_exit += r.exit_rank[0] == 1
    return {"win": wins / n, "draw": draws / n, "score": mean(sa), "opp_score": mean(sb),
            "first_exit": first_exit / n, "games": n}


def lair_pairs(n, seed=0):
    rng = random.Random(seed)
    return [(random_lair(rng), random_lair(rng)) for _ in range(n)]
