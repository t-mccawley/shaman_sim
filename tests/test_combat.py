"""Spell and melee attack tables."""

import random

import pytest

from shamansim.core.enums import HitOutcome, LevelDelta, Position
from shamansim.engine.combat import (
    MeleeTable,
    ResistTable,
    level_delta,
    spell_crit_multiplier,
    spell_hit_chance,
)


def _table(enemy_level: int, position: Position = Position.BEHIND, hit: float = 0.0) -> MeleeTable:
    return MeleeTable.build(
        level=60,
        enemy_level=enemy_level,
        weapon_skill=300,
        hit_pct=hit,
        crit_pct=10.0,
        enemy_armor=3731,
        position=position,
    )


def test_boss_attack_table_matches_classic() -> None:
    table = _table(63)
    assert table.miss == pytest.approx(0.08)
    assert table.dodge == pytest.approx(0.065)
    assert table.parry == 0.0
    assert table.glance == pytest.approx(0.40)
    assert table.crit == pytest.approx(0.10 - 0.048)
    assert (table.glance_min, table.glance_max) == pytest.approx((0.55, 0.75))
    assert table.armor_multiplier == pytest.approx(1 - 3731 / (3731 + 400 + 85 * 60))


def test_first_point_of_hit_is_suppressed_against_bosses() -> None:
    assert _table(63, hit=6.0).miss == pytest.approx(0.08 - 0.05)


def test_parry_only_from_front() -> None:
    assert _table(63, Position.FRONT).parry == pytest.approx(0.14)
    assert _table(60, Position.FRONT).parry == pytest.approx(0.05)


def test_same_level_table() -> None:
    table = _table(60)
    assert (table.miss, table.dodge, table.glance) == pytest.approx((0.05, 0.05, 0.10))
    assert table.crit == pytest.approx(0.10)


def test_auto_attack_roll_frequencies() -> None:
    table = _table(63)
    rng = random.Random(0)
    n = 200_000
    rolls = [table.roll_auto(rng) for _ in range(n)]
    assert rolls.count(HitOutcome.GLANCE) / n == pytest.approx(0.40, abs=0.005)
    assert rolls.count(HitOutcome.MISS) / n == pytest.approx(0.08, abs=0.003)


def test_special_attacks_never_glance() -> None:
    table = _table(63)
    rng = random.Random(0)
    assert HitOutcome.GLANCE not in {table.roll_special(rng) for _ in range(10_000)}


def test_spell_tables() -> None:
    assert spell_hit_chance(LevelDelta.PLUS_3, 0.0) == pytest.approx(0.83)
    assert spell_crit_multiplier(1.0) == pytest.approx(2.0)
    assert level_delta(60, 70) is LevelDelta.PLUS_3
    assert ResistTable.for_level_gap(0).roll_multiplier(random.Random(0)) == 1.0
