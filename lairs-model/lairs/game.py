"""Rules engine for the Lairs base game.

Each player explores the lair the *other* player built. Bots only ever see
an `Obs`, which exposes what their explorer has legitimately learned.

Rule readings that the rulebook leaves open are flags on `Rules`.
"""
import random
from collections import Counter, deque
from dataclasses import dataclass

from . import treasures as tr
from .dice import FACES, BLOB_TARGET, PIT_TARGET
from .lair import CHEST, EXIT, MONSTER, TRAP, step

W, Q, P = "W", "Q", "P"  # basic, Quickness, Perception
HAZARDS = (MONSTER, TRAP)
CONSERVE_SLOTS = 3


@dataclass
class Rules:
    # "When you move into a Monster or Trap in a Known space ... you must
    # fight/disarm it": read as an immediate mandatory check (0 dice allowed).
    known_entry_forces_check: bool = True
    first_exit_vp: int = 4
    second_exit_vp: int = 2
    monster_vp: tuple = (0, 0, 2, 6)  # cumulative VP for 0..3 defeated
    max_turns: int = 40  # per player; safety net if nobody ever exits


class Cubes:
    """Energy cubes in four zones: Fresh, Spent, fatigued (X), Conserved."""

    def __init__(self):
        self.z = {"F": Counter(), "S": Counter({W: 4, Q: 1, P: 1}), "X": Counter(), "C": Counter()}

    def refresh(self):
        self.z["F"] += self.z["S"]
        self.z["S"] = self.z["X"]
        self.z["X"] = Counter()

    def n(self, zone):
        return sum(self.z[zone].values())

    @property
    def spends(self):
        """How many cube-spends are available (a Conserved cube spends twice)."""
        return self.n("F") + 2 * self.n("C")

    def has(self, color):
        return self.z["F"][color] + self.z["C"][color] > 0

    def _move(self, color, a, b):
        assert self.z[a][color] > 0
        self.z[a][color] -= 1
        self.z[b][color] += 1

    def spend_color(self, color):
        if self.z["C"][color]:
            self._move(color, "C", "F")
        else:
            self._move(color, "F", "S")

    def spend_any(self, n, order=(W, P, Q)):
        for _ in range(n):
            color = next(c for c in order if self.has(c))
            self.spend_color(color)

    def fatigue_any(self, n):
        """Fatigue n cubes, choosing the least painful: Spent first, Conserved last."""
        for _ in range(n):
            for zone in ("S", "F", "C"):
                color = next((c for c in (W, P, Q) if self.z[zone][c]), None)
                if color:
                    self._move(color, zone, "X")
                    break

    def fatigue_fresh(self, n):
        """Fatigue n Fresh cubes (Conserved count as Fresh); shortfall hits any cube."""
        for i in range(n):
            for zone in ("F", "C"):
                color = next((c for c in (W, P, Q) if self.z[zone][c]), None)
                if color:
                    self._move(color, zone, "X")
                    break
            else:
                self.fatigue_any(n - i)
                return

    def conserve(self, colors):
        assert self.n("C") + len(colors) <= CONSERVE_SLOTS
        for c in colors:
            self._move(c, "F", "C")


class Player:
    def __init__(self, start):
        self.pos = start
        self.known = {start}
        self.cubes = Cubes()
        self.chests = self.monsters = self.traps = 0
        self.treasures = []
        self.exited = False
        self.exit_rank = None
        self.hustle_left = 0
        self.peer_free = None
        self.forced = False
        self.turns = 0
        self.strikes = 0

    @property
    def eligible(self):
        return self.chests >= 3 or self.monsters >= 3 or (self.chests >= 2 and self.monsters >= 2)


class Obs:
    """What a bot is allowed to see when it is asked for a decision."""

    def __init__(self, game, i):
        self._g, self._i = game, i
        p = game.players[i]
        self.pos, self.known = p.pos, p.known
        self.cubes = p.cubes
        self.spends = p.cubes.spends
        self.chests, self.monsters, self.traps = p.chests, p.monsters, p.traps
        self.eligible = p.eligible
        self.treasures = p.treasures
        self.display = game.display
        self.rng = game.bot_rng  # for bots to break ties; separate from the dice
        self.hustle_left, self.peer_free, self.forced = p.hustle_left, p.peer_free, p.forced
        self.turn = p.turns
        opp = game.players[1 - i]
        self.opp_exited = opp.exited
        self.opp_chests, self.opp_monsters = opp.chests, opp.monsters

    def has(self, color):
        return self.cubes.has(color)

    def feature(self, cell):
        assert cell in self.known, "peeking at an Unknown space"
        return self._g.features[self._i].get(cell)

    def open_dirs(self, cell):
        assert cell in self.known, "peeking at an Unknown space"
        return self._g.lairs[1 - self._i].open_dirs(cell)

    def monster_target(self, cell):
        assert cell in self.known
        return self._g.mtarget[self._i].get(cell, BLOB_TARGET)

    def backtrack_dests(self):
        return self._g.backtrack_dests(self._i)

    def my_score(self, extra=()):
        p = self._g.players[self._i]
        ctx = {"monsters": p.monsters, "traps": p.traps, "exited": p.exited}
        return tr.collection_score(list(p.treasures) + list(extra), ctx)


@dataclass
class Result:
    scores: tuple
    winner: object  # 0, 1 or None for a draw
    turns: tuple
    exit_rank: tuple
    chests: tuple
    monsters: tuple
    strikes: tuple
    exit_turn: tuple


class IllegalAction(Exception):
    pass


class Game:
    """lairs[i] is the lair built by player i; player i explores lairs[1 - i]."""

    def __init__(self, lairs, bots, seed=None, first=0, rules=None, deck=None):
        self.rng = random.Random(seed)
        self.bot_rng = random.Random(self.rng.random())
        self.rules = rules or Rules()
        self.lairs = lairs
        self.bots = bots
        self.first = first
        self.players = [Player(lairs[1 - i].start) for i in range(2)]
        # features[i] / mtarget[i]: live state of the lair player i explores
        self.features = [dict(lairs[1 - i].features) for i in range(2)]
        self.mtarget = [{} for _ in range(2)]
        self.deck = list(deck or tr.DECK)
        self.rng.shuffle(self.deck)
        self.display = [self.deck.pop() for _ in range(3)]
        self.exits = 0
        self.log = None  # set to a list to record (player, action) pairs

    # ---- helpers --------------------------------------------------------
    def roll(self, n):
        return sum(self.rng.choice(FACES) for _ in range(n))

    def backtrack_dests(self, i):
        """Known spaces reachable by moving only through Known Empty spaces."""
        p, feats, lair = self.players[i], self.features[i], self.lairs[1 - i]
        seen, out, dq = {p.pos}, {}, deque([(p.pos, 0)])
        while dq:
            u, d = dq.popleft()
            for _, v in lair.open_dirs(u):
                if v in seen or v not in p.known:
                    continue
                seen.add(v)
                out[v] = d + 1
                if v not in feats:  # only Empty spaces can be passed through
                    dq.append((v, d + 1))
        return out

    def _strike(self, p, kind):
        p.strikes += 1
        if kind == MONSTER:
            p.cubes.fatigue_any(2)  # Hungry Blob: fatigue any two cubes
        else:
            p.cubes.fatigue_fresh(2)  # Greased Pit: fatigue two Fresh cubes

    def _enter(self, i, cell):
        p = self.players[i]
        was_known = cell in p.known
        p.known.add(cell)
        p.pos = cell
        f = self.features[i].get(cell)
        if f in HAZARDS:
            if not was_known:
                self._strike(p, f)
            elif self.rules.known_entry_forces_check:
                p.forced = True
        return f

    def _neighbour(self, i, d):
        p = self.players[i]
        for dd, v in self.lairs[1 - i].open_dirs(p.pos):
            if dd == d:
                return v
        raise IllegalAction(f"wall or edge to the {d}")

    # ---- actions --------------------------------------------------------
    def apply(self, i, action):
        """Apply one action for player i. Returns True if their turn is over."""
        p, feats = self.players[i], self.features[i]
        kind = action[0]
        here = feats.get(p.pos)
        in_hazard = here in HAZARDS
        if self.log is not None:
            self.log.append((i, action))

        def need(cond, msg):
            if not cond:
                raise IllegalAction(f"{action}: {msg}")

        if p.forced:
            need(kind == "check", "must fight/disarm first")
        hustle_left, peer_free = p.hustle_left, p.peer_free
        p.hustle_left, p.peer_free = 0, None  # any other action forfeits these

        if kind == "end":
            return True

        if kind == "check":
            n = action[1]
            need(in_hazard, "nothing to fight or disarm here")
            need(0 <= n <= p.cubes.spends, "cannot afford that many dice")
            p.forced = False
            p.cubes.spend_any(n)
            total = self.roll(n)
            if here == TRAP:
                if total >= PIT_TARGET:
                    p.traps += 1
                else:
                    self._strike(p, TRAP)
                del feats[p.pos]  # the trap is gone either way
            else:
                target = self.mtarget[i].get(p.pos, BLOB_TARGET)
                if total >= target:
                    p.monsters += 1
                    del feats[p.pos]
                else:
                    self._strike(p, MONSTER)
                    self.mtarget[i][p.pos] = target - total
            return False

        if kind == "creep":
            need(p.cubes.spends >= 1, "no cubes")
            v = self._neighbour(i, action[1])
            p.cubes.spend_any(1)
            self._enter(i, v)
            return False

        if kind == "hustle":
            if action[1] == Q:
                need(p.cubes.has(Q), "no Quickness cube")
                p.cubes.spend_color(Q)
            else:
                need(p.cubes.spends >= 2, "need two cubes")
                p.cubes.spend_any(2)
            p.hustle_left = 3
            return False

        if kind == "hmove":
            need(hustle_left > 0, "not hustling")
            v = self._neighbour(i, action[1])
            f = self._enter(i, v)
            p.hustle_left = 0 if f else hustle_left - 1
            return False

        if kind == "backtrack":
            need(p.cubes.has(Q), "no Quickness cube")
            need(action[1] in self.backtrack_dests(i), "not a legal backtrack")
            p.cubes.spend_color(Q)
            self._enter(i, action[1])
            return False

        if kind == "peer":
            need(not in_hazard, "cannot peer from a hazard space")
            v = self._neighbour(i, action[1])
            need(v not in p.known, "space already Known")
            if action[2] == P:
                need(p.cubes.has(P), "no Perception cube")
                p.cubes.spend_color(P)
            else:
                need(p.cubes.spends >= 2, "need two cubes")
                p.cubes.spend_any(2)
            p.known.add(v)
            p.peer_free = v
            return False

        if kind == "pmove":
            need(peer_free is not None, "no free move available")
            self._enter(i, peer_free)
            return False

        if kind == "open":
            need(here == CHEST, "no chest here")
            del feats[p.pos]
            p.chests += 1
            p.treasures.append(self.deck.pop())
            k = self.bots[i].choose_treasure(Obs(self, i))
            p.treasures.append(self.display[k])
            self.display[k] = self.deck.pop()
            return False

        if kind == "exit":
            need(here == EXIT and p.eligible, "cannot exit")
            p.exited = True
            self.exits += 1
            p.exit_rank = self.exits
            return True

        if kind == "conserve":
            need(not in_hazard, "cannot conserve in a hazard space")
            colors = action[1]
            need(1 <= len(colors) <= CONSERVE_SLOTS - p.cubes.n("C"), "no free slot")
            need(not Counter(colors) - p.cubes.z["F"], "cubes are not Fresh")
            p.cubes.conserve(colors)
            return True

        raise IllegalAction(f"unknown action {action}")

    # ---- flow -----------------------------------------------------------
    def take_turn(self, i):
        p = self.players[i]
        p.turns += 1
        p.cubes.refresh()
        p.hustle_left, p.peer_free = 0, None
        for _ in range(200):
            if self.apply(i, self.bots[i].choose(Obs(self, i))):
                return
        raise RuntimeError("bot did not end its turn")

    def play(self):
        order = (self.first, 1 - self.first)
        while True:
            for i in order:
                self.take_turn(i)
                if self.players[1 - i].exited:  # that was the one final turn
                    return self.result()
            if min(p.turns for p in self.players) >= self.rules.max_turns:
                return self.result()

    def score(self, i):
        p, r = self.players[i], self.rules
        ctx = {"monsters": p.monsters, "traps": p.traps, "exited": p.exited}
        s = tr.collection_score(p.treasures, ctx) + r.monster_vp[p.monsters]
        if p.exit_rank == 1:
            s += r.first_exit_vp
        elif p.exit_rank == 2:
            s += r.second_exit_vp
        return s

    def result(self):
        ps = self.players
        scores = (self.score(0), self.score(1))
        if scores[0] != scores[1]:
            winner = 0 if scores[0] > scores[1] else 1
        else:
            winner = next((i for i in (0, 1) if ps[i].exit_rank == 1), None)
        return Result(
            scores, winner, tuple(p.turns for p in ps), tuple(p.exit_rank for p in ps),
            tuple(p.chests for p in ps), tuple(p.monsters for p in ps),
            tuple(p.strikes for p in ps), tuple(p.turns if p.exited else None for p in ps),
        )
