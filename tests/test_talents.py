"""Talent URL parsing, effects, and sheet stat swapping."""

import pytest

from shamansim import Character
from shamansim.core.enums import School, TalentTree
from shamansim.model.stats import EffectiveStats
from shamansim.spells.definitions import SpellId
from shamansim.talents.build import TalentBuild
from shamansim.talents.effects import TalentModifiers
from tests.conftest import CALC, NO_TALENTS, WEAPON

ENHANCEMENT_31 = CALC + "v2-050230031105102251"
HYBRID = CALC + "v20502031-0502300311041"


def test_enhancement_build_decodes() -> None:
    build = TalentBuild.from_url(ENHANCEMENT_31)
    assert build.points == {
        TalentTree.ELEMENTAL: 0,
        TalentTree.ENHANCEMENT: 31,
        TalentTree.RESTORATION: 0,
    }
    assert build.display_name == "Enhancement (0 / 31 / 0)"
    assert build.required_level == 40
    assert build.rank("Stormstrike") == 1


def test_row_requirement_enforced() -> None:
    # Elemental Fury (row 5) with only 23 points in the rows above it.
    with pytest.raises(ValueError, match="Elemental Fury needs 25 points"):
        TalentBuild.from_url(CALC + "v2550230130010305")


def test_prerequisite_enforced() -> None:
    # Flurry requires 3 points in Mental Dexterity; this build has 1.
    with pytest.raises(ValueError, match="Flurry requires 3 points in Mental Dexterity"):
        TalentBuild.from_url(CALC + "v2-055212000001")


def test_stale_version_rejected() -> None:
    with pytest.raises(ValueError, match="current format"):
        TalentBuild.from_url(ENHANCEMENT_31.replace("/v2-", "/v1-"))


def test_modifiers_use_per_rank_descriptions() -> None:
    mods = TalentModifiers.from_build(TalentBuild.from_url(ENHANCEMENT_31))
    assert mods.flurry_haste == pytest.approx(0.25)
    assert mods.windfury_multiplier == pytest.approx(1.40)
    assert mods.maelstrom_per_stack == pytest.approx(0.20)
    assert mods.improved_stormstrike_chance == pytest.approx(1.0)
    assert {SpellId.STORMSTRIKE, SpellId.RAGE_OF_THE_FARSEER} <= mods.granted_spells
    assert mods.unimplemented == ()


def test_hybrid_modifiers() -> None:
    mods = TalentModifiers.from_build(TalentBuild.from_url(HYBRID))
    assert mods.flurry_haste == pytest.approx(0.20)
    assert mods.elemental_devastation_crit_pct == pytest.approx(9.0)
    assert mods.damage_multiplier_spell[SpellId.EARTH_SHOCK] == pytest.approx(1.05)
    assert mods.cooldown_reduction[SpellId.FLAME_SHOCK] == pytest.approx(0.4)
    assert mods.spell_crit_damage_bonus[School.NATURE] == 0.0


def test_sheet_stat_talents_are_swapped() -> None:
    sheet = Character(
        display_name="c",
        level=40,
        intellect=100,
        spirit=50,
        mana=2000,
        attack_power=800,
        melee_crit=10,
        weapon=WEAPON,
        talents_on_sheet=ENHANCEMENT_31,
    )
    stats = EffectiveStats.build(sheet, NO_TALENTS)
    # Sheet had Mental Dexterity 3 (+100% Int as AP) and Thundering Strikes 5.
    assert stats.attack_power == pytest.approx(700)
    assert stats.melee_crit == pytest.approx(5)
    assert stats.spell_power.general == pytest.approx(-30)  # Mental Quickness removed
    back = EffectiveStats.build(sheet, TalentBuild.from_url(ENHANCEMENT_31))
    assert back.attack_power == pytest.approx(800)
    assert back.melee_crit == pytest.approx(10)
