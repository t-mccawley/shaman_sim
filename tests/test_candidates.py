"""Candidate planning and validation."""

from shamansim import (
    Character,
    Encounter,
    EncounterType,
    MetaConfig,
    Rotation,
    RotationFunction,
    SimState,
    SpellChoice,
    SpellId,
    WeaponImbue,
)
from shamansim.experiment.candidates import CandidatePlan, plan_candidates
from shamansim.spells.definitions import Spellbook
from shamansim.talents.build import TalentBuild
from tests.conftest import CALC, WEAPON

ENHANCEMENT_31 = TalentBuild.from_url(CALC + "v2-050230031105102251")
ELEMENTAL_31 = TalentBuild.from_url(CALC + "v25502301320103051")
META = MetaConfig(iterations=1)


def _idle(s: SimState) -> SpellChoice:
    return None


def _storm(s: SimState) -> SpellChoice:
    return s.spells.stormstrike if s.spells.stormstrike.ready else None


def _storm_if_known(s: SimState) -> SpellChoice:
    return s.spells.stormstrike if s.spells.stormstrike.known else None


def _rotation(
    function: RotationFunction, imbue: WeaponImbue = WeaponImbue.NONE, **ranks: int
) -> Rotation:
    return Rotation(
        display_name=function.__name__,
        description="",
        encounter_type=EncounterType.SINGLE_TARGET,
        rotation_function=function,
        weapon_imbue=imbue,
        rank_overrides={SpellId[k.upper()]: v for k, v in ranks.items()},
    )


def _plan(
    character: Character,
    dummy: Encounter,
    spellbook: Spellbook,
    rotations: list[Rotation],
    talents: list[TalentBuild],
) -> CandidatePlan:
    return plan_candidates([character], [dummy], rotations, talents, spellbook, META)


def test_valid_candidates_are_numbered(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    plan = _plan(shaman, dummy, spellbook, [_rotation(_idle)], [ENHANCEMENT_31, ELEMENTAL_31])
    assert [c.number for c in plan.valid] == [1, 2]
    assert plan.invalid == []


def test_rotation_using_untalented_spell_is_invalid(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    plan = _plan(shaman, dummy, spellbook, [_rotation(_storm)], [ENHANCEMENT_31, ELEMENTAL_31])
    assert [c.talents for c in plan.valid] == [ENHANCEMENT_31]
    assert plan.invalid[0].reasons == (
        "rotation uses Stormstrike, which requires the Stormstrike talent",
    )


def test_checking_known_is_allowed(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    plan = _plan(shaman, dummy, spellbook, [_rotation(_storm_if_known)], [ELEMENTAL_31])
    assert len(plan.valid) == 1


def test_talent_level_mismatch_is_invalid(dummy: Encounter, spellbook: Spellbook) -> None:
    level_30 = Character(
        display_name="c", level=30, intellect=80, spirit=80, mana=1500, weapon=WEAPON
    )
    plan = _plan(level_30, dummy, spellbook, [_rotation(_idle)], [ENHANCEMENT_31])
    assert plan.invalid[0].reasons == ("talents require level 40, character is level 30",)


def test_unlearned_imbue_is_invalid(dummy: Encounter, spellbook: Spellbook) -> None:
    level_30 = Character(
        display_name="c", level=30, intellect=80, spirit=80, mana=1500, weapon=WEAPON
    )
    talents_30 = TalentBuild.from_url(CALC + "v2-050230031151")  # 21 points
    rotation = _rotation(_idle, WeaponImbue.WINDFURY)
    plan = _plan(level_30, dummy, spellbook, [rotation], [talents_30])
    assert talents_30.required_level == 30
    assert plan.invalid[0].reasons == (
        "weapon imbue: Windfury Weapon is first learned at level 40 (character is 30)",
    )


def test_bad_rank_override_is_invalid(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    plan = _plan(shaman, dummy, spellbook, [_rotation(_idle, lightning_bolt=9)], [ENHANCEMENT_31])
    assert plan.invalid[0].reasons == (
        "rank override: Lightning Bolt has no rank 9 in configs/spellbook.py",
    )
