import random
from fractions import Fraction

import pytest

from lairs import treasures as tr
from lairs.bots import HeuristicBot, Params, PassBot
from lairs.dice import dist, kill_plan, p_success
from lairs.game import Cubes, Game, IllegalAction, P, Q, W
from lairs.lair import Lair, random_lair
from lairs.optimize import mutate

OPEN = """
+---+---+---+---+---+---+
| S   .   M   .   .   C |
+   +   +   +   +   +   +
| T   .   .   .   .   . |
+   +   +   +   +   +   +
| C   .   .   .   .   . |
+   +   +   +   +   +   +
| .   .   M   .   T   . |
+   +   +   +   +   +   +
| .   .   .   .   .   . |
+   +   +   +   +   +   +
| E   .   M   T   .   C |
+---+---+---+---+---+---+
"""


def lair_with(text, walls=()):
    base = Lair.from_text(text)
    return Lair(set(base.walls) | set(walls), base.features)


def game(lair=None, seed=0):
    lair = lair or Lair.from_text(OPEN)
    g = Game([lair, lair], [PassBot(), PassBot()], seed=seed)
    g.players[0].cubes.refresh()
    return g, g.players[0]


def test_dice():
    assert abs(sum(dist(3).values()) - 1) < 1e-12
    assert abs(p_success(2, 5) - 23 / 36) < 1e-12
    assert abs(p_success(2, 6) - 13 / 36) < 1e-12
    assert p_success(1, 5) == 0
    assert kill_plan(6, 2.0)[6][1] in (2, 3)


def test_cubes_refresh_and_conserve():
    c = Cubes()
    c.refresh()
    assert c.spends == 6
    c.spend_any(2)
    assert c.z["S"][W] == 2 and c.has(Q) and c.has(P)
    c.conserve((Q,))
    assert c.spends == 5  # 3 fresh + conserved cube twice
    c.spend_color(Q)
    c.spend_color(Q)
    assert not c.has(Q) and c.z["S"][Q] == 1


def test_fatigue_rules():
    c = Cubes()
    c.refresh()
    c.spend_any(1)
    c.fatigue_any(2)  # spent cube first, then a fresh one
    assert c.n("S") == 0 and c.n("F") == 4 and c.n("X") == 2
    c.spend_any(3)
    c.fatigue_fresh(2)  # only one Fresh left: shortfall falls on any cube
    assert c.n("F") == 0 and c.n("X") == 4 and c.n("S") == 2
    c.refresh()
    assert c.n("F") == 2 and c.n("S") == 4


def test_rulebook_scoring_example():
    by = {t.name: t for t in tr.DECK}
    hand = [by[n] for n in ("Tranquil Goblet", "Scroll of Harmony", "Moon Shard", "Sun Shard")]
    assert tr.face_up_score(hand, {}) == 1 + 5 + 3 + 3
    hand += [by["Stone Idol"], by["Storm Orb"]]
    assert tr.collection_score(hand) >= 14


def test_text_roundtrip_and_random_lairs_are_legal():
    rng = random.Random(0)
    for _ in range(20):
        l = random_lair(rng)
        assert l.is_legal()
        l2 = Lair.from_text(l.to_text())
        assert l2.walls == l.walls and l2.features == l.features
        assert mutate(l, rng).is_legal()


def test_legality_rules():
    assert any("walls" in p for p in Lair.from_text(OPEN).problems())
    # wall off the top-right corner
    sealed = Lair(set(random_lair(random.Random(1)).walls), Lair.from_text(OPEN).features)
    walls = [((0, 4), (0, 5)), ((0, 5), (1, 5))] + [((r, 0), (r, 1)) for r in range(6)] + \
            [((r, 2), (r, 3)) for r in range(6)] + [((r, 4), (r, 5)) for r in range(1, 6)]
    assert any("unreachable" in p for p in Lair(walls[:20], sealed.features).problems())


def test_peril_rule():
    # Start in a 1-wide corridor along row A: S M M C ... the chest sits behind two Blobs.
    feats = {(0, 0): "S", (0, 1): "M", (0, 2): "M", (0, 3): "C", (5, 0): "E", (5, 1): "C",
             (5, 2): "C", (5, 3): "M", (5, 4): "T", (5, 5): "T", (4, 5): "T"}
    walls = [((0, c), (1, c)) for c in range(4)] + [((0, 3), (0, 4))]
    spare = [((r, c), (r, c + 1)) for r in (2, 3, 4) for c in range(5)]
    bad = Lair(walls + spare[:15], feats)
    assert any("peril" in p for p in bad.problems())
    feats2 = dict(feats)
    feats2[(0, 2)], feats2[(3, 3)] = None, "M"
    feats2 = {k: v for k, v in feats2.items() if v}
    walls2 = walls[:4] + spare[:15] + [((2, 0), (3, 0))]
    good = Lair(walls2, feats2)
    assert good.problems() == []


def test_unknown_hazard_strikes_known_hazard_forces_check():
    g, p = game()
    g.apply(0, ("creep", "S"))  # A1 -> B1: unknown Greased Pit
    assert p.strikes == 1 and p.cubes.n("X") == 2 and not p.forced
    with pytest.raises(IllegalAction):
        g.apply(0, ("peer", "S", "any"))
    g.apply(0, ("creep", "N"))
    g.apply(0, ("creep", "S"))  # now Known: no strike, but must disarm
    assert p.strikes == 1 and p.forced
    with pytest.raises(IllegalAction):
        g.apply(0, ("creep", "N"))
    g.apply(0, ("check", 0))  # rolling nothing fails; trap is removed regardless
    assert p.strikes == 2 and (1, 0) not in g.features[0] and not p.forced


def test_hustle_peer_backtrack():
    g, p = game()
    g.apply(0, ("hustle", Q))
    g.apply(0, ("hmove", "E"))
    g.apply(0, ("hmove", "E"))  # A3: unknown Blob ends the hustle and strikes
    assert p.pos == (0, 2) and p.strikes == 1 and p.hustle_left == 0
    with pytest.raises(IllegalAction):
        g.apply(0, ("hmove", "E"))
    g, p = game()
    g.apply(0, ("peer", "E", P))
    assert p.pos == (0, 0) and (0, 1) in p.known
    g.apply(0, ("pmove",))
    g.apply(0, ("creep", "S"))
    g.apply(0, ("creep", "S"))
    p.cubes.refresh()
    assert g.backtrack_dests(0) == {(1, 1): 1, (0, 1): 2, (0, 0): 3}
    g.apply(0, ("backtrack", (0, 0)))
    assert p.pos == (0, 0)


def test_fight_damage_persists():
    g, p = game(seed=1)
    g.apply(0, ("creep", "E"))
    g.apply(0, ("creep", "E"))
    assert p.strikes == 1
    g.roll = lambda n: 4
    g.apply(0, ("check", 2))
    assert g.mtarget[0][(0, 2)] == 2 and p.monsters == 0 and p.strikes == 2
    p.cubes.refresh()
    g.apply(0, ("check", 1))
    assert p.monsters == 1 and (0, 2) not in g.features[0]


def test_exit_requirements_and_final_turn():
    g, p = game()
    p.pos = (5, 0)
    with pytest.raises(IllegalAction):
        g.apply(0, ("exit",))
    p.chests, p.monsters = 2, 2
    assert g.apply(0, ("exit",)) and p.exit_rank == 1
    lair = Lair.from_text(OPEN)

    class Leaver(PassBot):
        def choose(self, o):
            return ("exit",)

    g = Game([lair, lair], [Leaver(), PassBot()], seed=0)
    g.players[0].pos, g.players[0].chests = (5, 0), 3
    r = g.play()
    assert r.turns == (1, 1) and r.scores == (4, 0) and r.winner == 0


@pytest.mark.parametrize("explore", ["creep", "hustle", "peer"])
@pytest.mark.parametrize("fight", ["always", "never"])
@pytest.mark.parametrize("exit_when", ["asap", "chests", "all"])
def test_bots_always_finish_legally(explore, fight, exit_when):
    rng = random.Random(42)
    a = HeuristicBot(Params(explore=explore, fight=fight, exit_when=exit_when, whittle=True, disarm_stumbled=True))
    b = HeuristicBot(Params(explore=explore, fight=fight, exit_when=exit_when, conserve=False))
    for s in range(25):
        r = Game([random_lair(rng), random_lair(rng)], [a, b], seed=s, first=s % 2).play()
        assert r.exit_rank[0] or r.exit_rank[1], "nobody ever got out"
