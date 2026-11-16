"""Treasure cards and end-of-game collection scoring.

!!! PLACEHOLDER DECK !!!
The rulebook does not list the 22 Treasure cards. Only the cards marked
`from_rulebook=True` are taken from its examples; the rest are invented to
have a similar texture (low base scores, set/keyword combos). Replace DECK
with the real cards for accurate treasure values.
"""
from dataclasses import dataclass
from itertools import combinations

MAX_FACE_UP = 4
FACE_DOWN_VALUE = 1


@dataclass(frozen=True)
class Treasure:
    name: str
    type: str
    base: int
    keywords: tuple = ()
    bonus: tuple = None  # (kind, *args), see _bonus
    from_rulebook: bool = False


DECK = (
    Treasure("Tome of Divinity", "book", 1, ("harmony",), ("other_of_type", "book", 3), True),
    Treasure("Tome of Shadows", "book", 1, ("valor",), ("other_of_type", "book", 3)),
    Treasure("Tome of Ages", "book", 2),
    Treasure("Tranquil Goblet", "cup", 1, ("harmony",), ("other_of_type", "cup", 3), True),
    Treasure("Battle Chalice", "cup", 1, ("valor",), ("other_of_type", "cup", 3)),
    Treasure("Gilded Cup", "cup", 2),
    Treasure("Scroll of Harmony", "scroll", 3, (), ("per_keyword", "harmony", 2), True),
    Treasure("Scroll of Valor", "scroll", 3, (), ("per_keyword", "valor", 2)),
    Treasure("Moon Shard", "shard", 1, (), ("different_same_type", 2), True),
    Treasure("Sun Shard", "shard", 1, (), ("different_same_type", 2), True),
    Treasure("Star Shard", "shard", 1, (), ("different_same_type", 2)),
    Treasure("Warrior's Amulet", "amulet", 1, ("valor",), ("per_monster", 1), True),
    Treasure("Trapper's Amulet", "amulet", 1, (), ("per_trap", 1)),
    Treasure("Wayfinder's Amulet", "amulet", 1, (), ("exited", 2)),
    Treasure("Stone Idol", "statue", 2),
    Treasure("Jade Idol", "statue", 1, ("harmony",), ("per_type", "statue", 2)),
    Treasure("Bronze Idol", "statue", 1, ("valor",), ("per_type", "statue", 2)),
    Treasure("Crown of Kings", "crown", 3),
    Treasure("Crown of Thorns", "crown", 2, ("valor",)),
    Treasure("Seer's Orb", "orb", 1, (), ("distinct_types", 4, 3)),
    Treasure("Storm Orb", "orb", 2),
    Treasure("Serene Orb", "orb", 2, ("harmony",)),
)
assert len(DECK) == 22


def _bonus(card, others, ctx):
    b = card.bonus
    if b is None:
        return 0
    kind = b[0]
    if kind == "other_of_type":
        return b[2] if any(o.type == b[1] for o in others) else 0
    if kind == "per_type":
        return b[2] * sum(o.type == b[1] for o in others)
    if kind == "per_keyword":
        return b[2] * sum(b[1] in o.keywords for o in others)
    if kind == "different_same_type":
        return b[1] if any(o.type == card.type and o.name != card.name for o in others) else 0
    if kind == "per_monster":
        return b[1] * ctx.get("monsters", 0)
    if kind == "per_trap":
        return b[1] * ctx.get("traps", 0)
    if kind == "exited":
        return b[1] if ctx.get("exited") else 0
    if kind == "distinct_types":
        return b[2] if len({o.type for o in others} | {card.type}) >= b[1] else 0
    raise ValueError(kind)


def face_up_score(cards, ctx):
    return sum(c.base + _bonus(c, [o for o in cards if o is not c], ctx) for c in cards)


def collection_score(cards, ctx=None):
    """Best score: choose up to four cards to keep face-up, the rest score 1 each."""
    ctx = ctx or {}
    cards = list(cards)
    k = min(MAX_FACE_UP, len(cards))
    best = 0
    for up in combinations(cards, k):
        best = max(best, face_up_score(up, ctx) + FACE_DOWN_VALUE * (len(cards) - k))
    return best
