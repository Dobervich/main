"""Explorer policies. One parameterised heuristic bot; every knob is a strategy question."""
import heapq
from dataclasses import dataclass

from .dice import PIT_TARGET, dice_needed, p_success
from .game import P, Q, W, CONSERVE_SLOTS
from .lair import CHEST, EXIT, MONSTER, TRAP, direction


@dataclass(frozen=True)
class Params:
    explore: str = "hustle"       # how to enter Unknown spaces: 'creep' | 'hustle' | 'peer'
    use_p_peer: bool = True       # Peer with the Perception cube whenever it is available
    fight: str = "always"         # 'always' seek out Blobs | 'never' unless required to exit
    fight_p: float = 0.6          # buy the fewest dice giving at least this chance to win
    whittle: bool = False         # attack with too few dice just to bank damage
    wait_to_fight: bool = True    # sit in a Blob's space until enough cubes, rather than leave
    disarm_p: float = 0.6         # same threshold for traps (if unaffordable: roll no dice)
    disarm_stumbled: bool = False # disarm a trap you blundered into, rather than walking on
    exit_when: str = "asap"       # 'asap' | 'chests' (all 3 opened) | 'all' (3 chests + 3 Blobs)
    conserve: bool = True         # Conserve leftover Fresh cubes instead of just ending
    monster_cost: int = 4         # path-planning penalty for routing through a known Blob
    trap_cost: int = 3            # ... and through a known Pit


class PassBot:
    """Does nothing. Used as the 'opponent' in solo runs."""

    def choose(self, o):
        return ("check", 0) if o.forced else ("end",)

    def choose_treasure(self, o):
        return 0


class HeuristicBot:
    def __init__(self, params=None, **kw):
        self.p = params or Params(**kw)

    # ---- treasure -------------------------------------------------------
    def choose_treasure(self, o):
        return max(range(len(o.display)), key=lambda k: o.my_score([o.display[k]]))

    # ---- top level ------------------------------------------------------
    def choose(self, o):
        here = o.feature(o.pos)
        if o.forced:
            return ("check", self._dice(o, here, forced=True))
        if here == CHEST:
            return ("open",)
        if here == EXIT and o.eligible and self._want_exit(o):
            return ("exit",)
        if here == MONSTER and self._wants_fight(o):
            n = self._dice(o, MONSTER)
            if n:
                return ("check", n)
            if self.p.wait_to_fight:
                return ("end",)
        if here == TRAP and self.p.disarm_stumbled:
            n = self._dice(o, TRAP)
            if n:
                return ("check", n)
        return self._move(o)

    # ---- judgement calls ------------------------------------------------
    def _want_exit(self, o):
        w = self.p.exit_when
        if o.opp_exited or w == "asap":
            return True
        if w == "chests":
            return o.chests >= 3
        return o.chests >= 3 and o.monsters >= 3

    def _wants_fight(self, o):
        if o.monsters >= 3:
            return False
        if self.p.fight == "always" or self.p.exit_when == "all":
            return not (o.eligible and self._want_exit(o))
        return self._stuck(o)

    def _stuck(self, o):
        """Not yet able to exit, and nothing left to find but Blobs."""
        if o.eligible:
            return False
        dist, _ = self._plan(o)
        return not any(c not in o.known or o.feature(c) == CHEST for c in dist)

    def _dice(self, o, kind, forced=False):
        s = o.spends
        if kind == TRAP:
            n = dice_needed(PIT_TARGET, self.p.disarm_p)
            return n if s >= n else 0
        if forced and not self._wants_fight(o):
            return 0  # just passing through: take the hit
        n = dice_needed(o.monster_target(o.pos), self.p.fight_p)
        if s >= n:
            return n
        return s if self.p.whittle else 0

    # ---- movement -------------------------------------------------------
    def _plan(self, o):
        """Dijkstra over Known spaces; Unknown neighbours are leaves (the frontier)."""
        dist, prev = {o.pos: 0}, {}
        pq = [(0, o.pos)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u] or (u not in o.known):
                continue
            for _, v in o.open_dirs(u):
                nd = d + 1
                if v in o.known:
                    f = o.feature(v)
                    nd += self.p.monster_cost if f == MONSTER else self.p.trap_cost if f == TRAP else 0
                if nd < dist.get(v, 1e9):
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        return dist, prev

    def _target(self, o, dist):
        def nearest(pred):
            cs = [c for c in dist if c != o.pos and pred(c)]
            if not cs:
                return None
            best = min(dist[c] for c in cs)
            # random tie-break: a fixed preference (say north-west first) is exploitable by lair builders
            return o.rng.choice(sorted(c for c in cs if dist[c] == best))

        known = lambda f: (lambda c: c in o.known and o.feature(c) == f)
        leaving = o.eligible and self._want_exit(o)
        if leaving:
            t = nearest(known(EXIT))
            if t:
                return t
        else:
            t = nearest(known(CHEST))
            if t:
                return t
            if self._wants_fight(o):
                t = nearest(known(MONSTER))
                if t:
                    return t
        t = nearest(lambda c: c not in o.known)
        if t:
            return t
        if not o.eligible:
            return nearest(known(MONSTER))
        return nearest(known(EXIT))

    def _end(self, o):
        f = o.feature(o.pos)
        free = CONSERVE_SLOTS - o.cubes.n("C")
        if self.p.conserve and f not in (MONSTER, TRAP) and free and o.cubes.n("F"):
            fresh = [c for c in (Q, P, W) for _ in range(o.cubes.z["F"][c])]
            return ("conserve", tuple(fresh[:free]))
        return ("end",)

    def _move(self, o):
        p = self.p
        if o.peer_free is not None and self._step_in_after_peer(o, o.peer_free):
            return ("pmove",)
        dist, prev = self._plan(o)
        target = self._target(o, dist)
        if target is None:
            return self._end(o)
        path = [target]
        while path[-1] != o.pos:
            path.append(prev[path[-1]])
        path = path[-2::-1]  # spaces to step through, in order
        nxt = path[0]
        d = direction(o.pos, nxt)
        unknown = nxt not in o.known

        if o.hustle_left and not (unknown and p.explore == "peer"):
            return ("hmove", d)

        in_hazard = o.feature(o.pos) in (MONSTER, TRAP)  # no Peering from a hazard space
        if unknown:
            if p.use_p_peer and o.has(P) and not in_hazard:
                return ("peer", d, P)
            if p.explore == "peer" and not in_hazard:
                return ("peer", d, "any") if o.spends >= 2 else self._end(o)
            if p.explore == "hustle":
                if o.has(Q):
                    return ("hustle", Q)
                if o.spends >= 2:
                    return ("hustle", "any")
            return ("creep", d) if o.spends else self._end(o)

        f = o.feature(nxt)
        if f == MONSTER and self._wants_fight(o):
            # Entering a Known Blob forces a fight: arrive with enough dice or wait.
            if o.spends - 1 < dice_needed(o.monster_target(nxt), p.fight_p) and not p.whittle:
                return self._end(o)

        known_len = next((k for k, c in enumerate(path) if c not in o.known), len(path))
        reach = known_len + (p.explore != "peer" and known_len < len(path))
        if o.has(Q):
            bt = o.backtrack_dests()
            far = max((k for k in range(known_len) if path[k] in bt), default=-1) + 1
            if far > 3:
                return ("backtrack", path[far - 1])
            if reach >= 2:
                return ("hustle", Q)
        if reach >= 3 and o.spends >= 2:
            return ("hustle", "any")
        return ("creep", d) if o.spends else self._end(o)

    def _step_in_after_peer(self, o, c):
        f = o.feature(c)
        if f == TRAP:
            return False
        if f == MONSTER:
            return self._wants_fight(o) and o.spends >= dice_needed(o.monster_target(c), self.p.fight_p)
        if f in (CHEST, EXIT):
            return True
        return any(v not in o.known for _, v in o.open_dirs(c))
