"""Effective stats: the character sheet re-talented for a candidate.

The sheet already includes the stat talents in `Character.talents_on_sheet`;
those are removed and the candidate's are applied. Strength and agility
are re-derived into attack power and melee crit, so talents that scale them
(none so far) change those too. Intellect's effect on spell crit is not modeled.
"""

from dataclasses import dataclass, replace

from shamansim.core.constants import ATTACK_POWER_PER_AGILITY, ATTACK_POWER_PER_STRENGTH
from shamansim.model.character import (
    Character,
    SchoolValues,
    mana_from_intellect,
    melee_crit_per_agility,
)
from shamansim.talents.build import TalentBuild
from shamansim.talents.effects import StatTalents


@dataclass(frozen=True, slots=True, kw_only=True)
class EffectiveStats:
    """Stats used by the simulator. Percent values are in percent."""

    strength: float
    agility: float
    intellect: float
    mana: float
    base_mana: float
    attack_power: float
    melee_crit: float
    melee_hit: float
    spell_power: SchoolValues
    spell_crit: SchoolValues
    spell_hit: SchoolValues

    @classmethod
    def build(cls, character: Character, talents: TalentBuild) -> "EffectiveStats":
        """Swap the sheet's stat talents for `talents`."""
        sheet = sheet_stat_talents(character)
        new = StatTalents.from_build(talents)
        intellect = character.intellect / sheet.intellect_multiplier * new.intellect_multiplier
        strength = character.strength / sheet.strength_multiplier * new.strength_multiplier
        agility = character.agility / sheet.agility_multiplier * new.agility_multiplier
        crit_delta = new.crit_pct - sheet.crit_pct
        attack_power = (
            character.attack_power
            + attack_power_from(strength - character.strength, agility - character.agility)
            - sheet.attack_power_per_intellect * character.intellect
            + new.attack_power_per_intellect * intellect
        )
        spell_power_delta = (
            new.spell_power_per_intellect * intellect
            - sheet.spell_power_per_intellect * character.intellect
        )
        mana = (
            character.mana
            - mana_from_intellect(character.intellect)
            + mana_from_intellect(intellect)
        )
        return cls(
            strength=strength,
            agility=agility,
            intellect=intellect,
            mana=mana,
            base_mana=character.base_mana,
            attack_power=attack_power,
            melee_crit=character.melee_crit
            + crit_delta
            + (agility - character.agility) * melee_crit_per_agility(character.level),
            melee_hit=character.melee_hit,
            spell_power=replace(
                character.spell_power, general=character.spell_power.general + spell_power_delta
            ),
            spell_crit=replace(
                character.spell_crit, general=character.spell_crit.general + crit_delta
            ),
            spell_hit=character.spell_hit,
        )


def attack_power_from(strength: float, agility: float) -> float:
    """Attack power granted by strength and agility."""
    return ATTACK_POWER_PER_STRENGTH * strength + ATTACK_POWER_PER_AGILITY * agility


def sheet_stat_talents(character: Character) -> StatTalents:
    """Stat talents already included in the character sheet."""
    if not character.talents_on_sheet:
        return StatTalents()
    return StatTalents.from_build(TalentBuild.from_url(character.talents_on_sheet))
