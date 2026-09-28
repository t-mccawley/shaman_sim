"""Effective stats: the character sheet re-talented for a candidate.

The sheet already includes the stat talents in `Character.talents_on_sheet`;
those are removed and the candidate's are applied. Intellect's effect on
spell crit is not modeled.
"""

from dataclasses import dataclass, replace

from shamansim.model.character import Character, SchoolValues, mana_from_intellect
from shamansim.talents.build import TalentBuild
from shamansim.talents.effects import StatTalents


@dataclass(frozen=True, slots=True, kw_only=True)
class EffectiveStats:
    """Stats used by the simulator. Percent values are in percent."""

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
        sheet = (
            StatTalents.from_build(TalentBuild.from_url(character.talents_on_sheet))
            if character.talents_on_sheet
            else StatTalents()
        )
        new = StatTalents.from_build(talents)
        intellect = character.intellect / sheet.intellect_multiplier * new.intellect_multiplier
        crit_delta = new.crit_pct - sheet.crit_pct
        attack_power = (
            character.attack_power
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
            intellect=intellect,
            mana=mana,
            base_mana=character.base_mana,
            attack_power=attack_power,
            melee_crit=character.melee_crit + crit_delta,
            melee_hit=character.melee_hit,
            spell_power=replace(
                character.spell_power, general=character.spell_power.general + spell_power_delta
            ),
            spell_crit=replace(
                character.spell_crit, general=character.spell_crit.general + crit_delta
            ),
            spell_hit=character.spell_hit,
        )
