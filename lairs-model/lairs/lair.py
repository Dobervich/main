"""Lair boards: walls, features, legality rules, text format, random generation."""
import random
from collections import deque

N = 6
DIRS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1)}
START, EXIT, CHEST, MONSTER, TRAP = "S", "E", "C", "M", "T"
REQUIRED = {START: 1, EXIT: 1, CHEST: 3, MONSTER: 3, TRAP: 3}
MAX_WALLS, MIN_WALLS = 20, 17
CELLS = [(r, c) for r in range(N) for c in range(N)]


def edge(a, b):
    return (a, b) if a < b else (b, a)


ALL_EDGES = sorted(
    {edge((r, c), (r + dr, c + dc)) for r, c in CELLS for dr, dc in ((1, 0), (0, 1))
     if r + dr < N and c + dc < N}
)


def step(cell, d):
    dr, dc = DIRS[d]
    r, c = cell[0] + dr, cell[1] + dc
    return (r, c) if 0 <= r < N and 0 <= c < N else None


def direction(a, b):
    for d, (dr, dc) in DIRS.items():
        if (a[0] + dr, a[1] + dc) == b:
            return d
    raise ValueError(f"{a} and {b} are not adjacent")


def name(cell):
    return "ABCDEF"[cell[0]] + str(cell[1] + 1)


class Lair:
    def __init__(self, walls, features):
        self.walls = frozenset(walls)
        self.features = dict(features)
        self._nb = {}
        for cell in CELLS:
            out = []
            for d in DIRS:
                n = step(cell, d)
                if n is not None and edge(cell, n) not in self.walls:
                    out.append((d, n))
            self._nb[cell] = out

    def open_dirs(self, cell):
        """[(direction, neighbour)] for every side of the cell that is not a wall."""
        return self._nb[cell]

    @property
    def start(self):
        return next(c for c, f in self.features.items() if f == START)

    def cells_with(self, f):
        return [c for c, g in self.features.items() if g == f]

    # ---- legality -------------------------------------------------------
    def problems(self):
        out = []
        counts = {}
        for f in self.features.values():
            counts[f] = counts.get(f, 0) + 1
        for f, n in REQUIRED.items():
            if counts.get(f, 0) != n:
                out.append(f"need {n} of {f}, found {counts.get(f, 0)}")
        if not MIN_WALLS <= len(self.walls) <= MAX_WALLS:
            out.append(f"{len(self.walls)} walls (must use {MIN_WALLS}-{MAX_WALLS})")
        if out:
            return out
        start = self.start
        seen = {start}
        dq = deque([start])
        while dq:
            u = dq.popleft()
            for _, v in self._nb[u]:
                if v not in seen:
                    seen.add(v)
                    dq.append(v)
        if len(seen) < N * N:
            out.append(f"{N * N - len(seen)} unreachable spaces")
        # Peril rule: each Goal reachable via <=1 Trap and <=1 Monster.
        s0 = (start, 0, 0)
        seen = {s0}
        dq = deque([s0])
        ok = set()
        while dq:
            u, t, m = dq.popleft()
            ok.add(u)
            for _, v in self._nb[u]:
                f = self.features.get(v)
                nt, nm = t + (f == TRAP), m + (f == MONSTER)
                if nt > 1 or nm > 1:
                    continue
                s = (v, nt, nm)
                if s not in seen:
                    seen.add(s)
                    dq.append(s)
        for c, f in self.features.items():
            if f in (CHEST, EXIT) and c not in ok:
                out.append(f"peril rule broken for {f} at {name(c)}")
        return out

    def is_legal(self):
        return not self.problems()

    # ---- text format ----------------------------------------------------
    def to_text(self):
        lines = []
        for r in range(N + 1):
            row = "+"
            for c in range(N):
                solid = r in (0, N) or edge((r - 1, c), (r, c)) in self.walls
                row += ("---" if solid else "   ") + "+"
            lines.append(row)
            if r == N:
                break
            row = "|"
            for c in range(N):
                row += f" {self.features.get((r, c), '.')} "
                solid = c == N - 1 or edge((r, c), (r, c + 1)) in self.walls
                row += "|" if solid else " "
            lines.append(row)
        return "\n".join(lines)

    @classmethod
    def from_text(cls, text):
        lines = [l for l in text.strip("\n").split("\n")]
        walls, feats = set(), {}
        for r in range(N):
            cellrow = lines[2 * r + 1]
            for c in range(N):
                ch = cellrow[4 * c + 2]
                if ch != ".":
                    feats[(r, c)] = ch
                if c < N - 1 and cellrow[4 * c + 4] == "|":
                    walls.add(edge((r, c), (r, c + 1)))
                if r < N - 1 and lines[2 * r + 2][4 * c + 2] == "-":
                    walls.add(edge((r, c), (r + 1, c)))
        return cls(walls, feats)

    def __str__(self):
        return self.to_text()


def random_lair(rng=None, n_walls=MAX_WALLS):
    """Uniformly random legal lair (rejection sampling)."""
    rng = rng or random
    kinds = [f for f, n in REQUIRED.items() for _ in range(n)]
    while True:
        cells = rng.sample(CELLS, len(kinds))
        lair = Lair(rng.sample(ALL_EDGES, n_walls), dict(zip(cells, kinds)))
        if lair.is_legal():
            return lair
