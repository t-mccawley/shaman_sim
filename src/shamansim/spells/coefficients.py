"""Spell power coefficients, calculated from configured rank values.

Classic formula (reproduces wowsims/classic values for ranks learned at level 20+):
    cast / instant = clamp(cast_time, 1.5, 3.5) / 3.5     (instants count as 1.5 s)
    totem attack   = attack_interval / 3.5
    dot            = dot_duration / 15, split across ticks
each times the spell's scale (mechanics.py). Weapon strikes and buffs have none.

Unlike Classic, there is no penalty for ranks learned below level 20: the
Forever beta client stores the full coefficient on every rank.
"""

from dataclasses import dataclass
from typing import Final

from shamansim.core.enums import CastKind
from shamansim.spells.definitions import SpellMechanics, SpellRank

MIN_CAST_TIME: Final = 1.5
MAX_CAST_TIME: Final = 3.5
CAST_TIME_DIVISOR: Final = 3.5
DOT_DURATION_DIVISOR: Final = 15.0

# Standard Classic scale factors.
AOE_SCALE: Final = 1.0 / 3.0

# Weapon imbue procs (wowsims/classic).
IMBUE_PROC_COEFFICIENT: Final = 0.1


@dataclass(frozen=True, slots=True)
class RankCoefficients:
    """Calculated coefficients for one rank.

    `direct` applies per hit (per attack for totems); `dot_per_tick` per DoT tick.
    """

    direct_base: float
    direct: float
    dot_base: float
    dot_per_tick: float


def direct_base(mechanics: SpellMechanics, rank: SpellRank) -> float:
    """Unscaled coefficient of one direct hit."""
    if mechanics.weapon_damage or mechanics.cast_kind is CastKind.BUFF:
        return 0.0
    if rank.totem is not None:
        return rank.totem.attack_interval / CAST_TIME_DIVISOR
    return min(max(rank.cast_time, MIN_CAST_TIME), MAX_CAST_TIME) / CAST_TIME_DIVISOR


def calculate(mechanics: SpellMechanics, rank: SpellRank) -> RankCoefficients:
    """Coefficients for `rank` of the spell described by `mechanics`."""
    base = direct_base(mechanics, rank)
    dot_base = rank.dot.duration / DOT_DURATION_DIVISOR if rank.dot else 0.0
    dot_ticks = rank.dot.ticks if rank.dot else 1
    return RankCoefficients(
        direct_base=base,
        direct=base * mechanics.direct_scale,
        dot_base=dot_base,
        dot_per_tick=dot_base * mechanics.dot_scale / dot_ticks,
    )
