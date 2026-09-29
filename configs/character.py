"""Character stats, copied from the in-game character sheet (after gear and buffs).

Percent stats are in percent (5.5 = 5.5%). Set `talents_on_sheet` to the talent
link active when copying the sheet so its stat talents can be swapped per candidate.
"""

from shamansim import Character, SchoolValues, Water, Weapon

CHARACTERS: list[Character] = [
    Character(
        display_name="L20",
        level=20,
        intellect=50,
        spirit=50,
        mana=600,
        mp5=0,
        attack_power=100,
        melee_crit=10.05,
        melee_hit=0.0,
        weapon_skill_bonus=0,
        spell_power=SchoolValues(general=0),
        spell_crit=SchoolValues(general=9.92),
        spell_hit=SchoolValues(general=0),
        weapon=Weapon(
            name="Severing Axe", min_damage=18, max_damage=27, speed=3.2, two_handed=True
        ),
        water=Water.ICE_COLD_MILK,
        talents_on_sheet=None,
    ),
]
