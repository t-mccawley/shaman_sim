"""Shared test fixtures."""

import pytest

from shamansim import (
    BuffData,
    Character,
    DotData,
    Encounter,
    EncounterType,
    ImbueRank,
    LevelDelta,
    SpellId,
    SpellRank,
    TotemData,
    Weapon,
    WeaponImbue,
)
from shamansim.core.enums import TalentTree
from shamansim.spells.definitions import Spellbook
from shamansim.spells.mechanics import build_catalog, build_imbue_catalog
from shamansim.talents.build import TalentBuild

CALC = "https://www.wowhead.com/forever/talent-calc/shaman/"
NO_TALENTS = TalentBuild(url="", ranks={}, points=dict.fromkeys(TalentTree, 0))
WEAPON = Weapon(name="Test Mace", min_damage=100, max_damage=100, speed=3.0, two_handed=True)


@pytest.fixture
def spellbook() -> Spellbook:
    """Small spellbook independent of configs/spellbook.py."""
    return Spellbook(
        spells=build_catalog(
            {
                SpellId.LIGHTNING_BOLT: [
                    SpellRank(
                        rank=1, level=1, min_damage=15, max_damage=17, mana_cost=15, cast_time=1.5
                    ),
                    SpellRank(
                        rank=7,
                        level=38,
                        min_damage=142,
                        max_damage=160,
                        mana_cost=135,
                        cast_time=2.5,
                    ),
                ],
                SpellId.EARTH_SHOCK: [
                    SpellRank(
                        rank=5, level=36, min_damage=135, max_damage=142, mana_cost=240, cooldown=6
                    ),
                ],
                SpellId.FLAME_SHOCK: [
                    SpellRank(
                        rank=4,
                        level=40,
                        min_damage=89,
                        max_damage=89,
                        mana_cost=250,
                        cooldown=6,
                        dot=DotData(damage=84, duration=12, ticks=4),
                    ),
                ],
                SpellId.FIRE_NOVA: [
                    SpellRank(
                        rank=3, level=32, min_damage=195, max_damage=219, mana_cost=280, cooldown=10
                    ),
                ],
                SpellId.SEARING_TOTEM: [
                    SpellRank(
                        rank=4,
                        level=40,
                        min_damage=26,
                        max_damage=34,
                        mana_cost=110,
                        totem=TotemData(duration=45, attack_interval=2.5),
                    ),
                ],
                SpellId.STORMSTRIKE: [
                    SpellRank(rank=1, level=40, mana_cost=125, cooldown=8),
                ],
                SpellId.RAGE_OF_THE_FARSEER: [
                    SpellRank(
                        rank=1,
                        level=1,
                        cooldown=180,
                        buff=BuffData(duration=25, attack_speed_pct=30),
                    ),
                ],
            }
        ),
        imbues=build_imbue_catalog(
            {
                WeaponImbue.ROCKBITER: [ImbueRank(rank=5, level=34, value=355)],
                WeaponImbue.FLAMETONGUE: [ImbueRank(rank=4, level=36, value=1728)],
                WeaponImbue.WINDFURY: [ImbueRank(rank=2, level=40, value=221)],
            }
        ),
    )


@pytest.fixture
def shaman() -> Character:
    """Level 40 shaman with effectively infinite mana and a fixed-damage weapon."""
    return Character(
        display_name="Test",
        level=40,
        intellect=100,
        spirit=100,
        mana=1_000_000,
        attack_power=700,
        weapon=WEAPON,
    )


@pytest.fixture
def dummy() -> Encounter:
    """Immortal same-level target without armor, attacked from behind, 60 s."""
    return Encounter(
        display_name="Dummy",
        description="",
        encounter_type=EncounterType.SINGLE_TARGET,
        duration=60,
        enemy_count=1,
        enemy_health=1e12,
        enemy_level_delta=LevelDelta.SAME,
    )
