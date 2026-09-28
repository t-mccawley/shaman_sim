"""Character stats, copied from the in-game character sheet (after gear and buffs).

Percent stats are in percent (5.5 = 5.5%). Set `talents_on_sheet` to the talent
link active when copying the sheet so its stat talents can be swapped per candidate.
"""

from shamansim import Character, SchoolValues, Water, Weapon

CHARACTERS: list[Character] = [
    Character(
        display_name="Enh L40",
        level=40,
        intellect=110,
        spirit=100,
        mana=2100,
        mp5=0,
        attack_power=620,
        melee_crit=7.0,
        melee_hit=2.0,
        weapon_skill_bonus=0,
        spell_power=SchoolValues(general=0),
        spell_crit=SchoolValues(general=4.0),
        spell_hit=SchoolValues(general=0),
        weapon=Weapon(
            name="Two-hand mace", min_damage=95, max_damage=143, speed=3.6, two_handed=True
        ),
        water=Water.MELON_JUICE,
        talents_on_sheet=None,
    ),
]
