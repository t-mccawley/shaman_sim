"""Calculated spell power coefficients reproduce wowsims/classic."""

import pytest

from shamansim import DotData, SpellId, SpellRank, TotemData
from shamansim.spells.coefficients import calculate
from shamansim.spells.mechanics import SPELL_MECHANICS

# Classic ranks learned at level 20+ (no Classic low-level penalty), with
# wowsims/classic coefficients: (spell, level, cast time, dot, totem, direct, dot per tick).
WOWSIMS_CASES = [
    (SpellId.LIGHTNING_BOLT, 20, 3.0, None, None, 0.857, 0.0),
    (SpellId.CHAIN_LIGHTNING, 32, 2.5, None, None, 0.714, 0.0),
    (SpellId.EARTH_SHOCK, 24, 0.0, None, None, 0.386, 0.0),
    (SpellId.FROST_SHOCK, 20, 0.0, None, None, 0.386, 0.0),
    (SpellId.FLAME_SHOCK, 28, 0.0, DotData(damage=56, duration=12, ticks=4), None, 0.214, 0.1),
    (SpellId.FIRE_NOVA, 22, 0.0, None, None, 0.143, 0.0),
    (SpellId.SEARING_TOTEM, 20, 0.0, None, TotemData(duration=35, attack_interval=2.5), 0.083, 0.0),
    (SpellId.MAGMA_TOTEM, 26, 0.0, None, TotemData(duration=20, attack_interval=2.0), 0.033, 0.0),
]


@pytest.mark.parametrize(
    ("spell", "level", "cast_time", "dot", "totem", "direct", "dot_per_tick"), WOWSIMS_CASES
)
def test_matches_wowsims(
    spell: SpellId,
    level: int,
    cast_time: float,
    dot: DotData | None,
    totem: TotemData | None,
    direct: float,
    dot_per_tick: float,
) -> None:
    rank = SpellRank(rank=1, level=level, cast_time=cast_time, dot=dot, totem=totem)
    result = calculate(SPELL_MECHANICS[spell], rank)
    assert result.direct == pytest.approx(direct, abs=0.0015)
    assert result.dot_per_tick == pytest.approx(dot_per_tick, abs=0.0015)


def test_low_ranks_get_full_coefficient() -> None:
    rank = SpellRank(rank=1, level=1, cast_time=1.5)
    assert calculate(SPELL_MECHANICS[SpellId.LIGHTNING_BOLT], rank).direct == pytest.approx(
        1.5 / 3.5
    )


def test_weapon_strikes_have_no_coefficient() -> None:
    rank = SpellRank(rank=1, level=40, cooldown=8)
    assert calculate(SPELL_MECHANICS[SpellId.STORMSTRIKE], rank).direct == 0.0
