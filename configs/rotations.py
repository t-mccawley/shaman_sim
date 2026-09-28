"""Rotations: priority functions called whenever the character can act.

Melee auto attacks run on their own; return a spell (e.g. `s.spells.stormstrike`)
to use it, or None to keep swinging. Picks on cooldown or unaffordable wait a
tick; the time lost is reported as "blocked".
"""

from shamansim import (
    EncounterType,
    Rotation,
    RotationFunction,
    SimState,
    SpellChoice,
    WeaponImbue,
)


def stormstrike(s: SimState) -> SpellChoice:
    """Stormstrike, then an empowered Earth Shock; Lightning Bolt at 5 Maelstrom stacks."""
    sb = s.spells
    target = s.target
    if sb.rage_of_the_farseer.known and sb.rage_of_the_farseer.ready:
        return sb.rage_of_the_farseer
    if sb.stormstrike.ready:
        return sb.stormstrike
    if target is not None and target.stormstruck and sb.earth_shock.ready:
        return sb.earth_shock
    if s.maelstrom_stacks == 5 and sb.lightning_bolt.ready:
        return sb.lightning_bolt
    return None


def shocks(s: SimState) -> SpellChoice:
    """Keep Flame Shock up, Earth Shock otherwise, keep a Searing Totem down."""
    sb = s.spells
    target = s.target
    if s.fire_totem is None and sb.searing_totem.ready:
        return sb.searing_totem
    if target is not None and not target.has_dot("Flame Shock") and sb.flame_shock.ready:
        return sb.flame_shock
    if sb.earth_shock.ready and s.mana_pct > 30:
        return sb.earth_shock
    return None


def caster(s: SimState) -> SpellChoice:
    """Flame Shock, then Lightning Bolt."""
    sb = s.spells
    target = s.target
    if target is not None and not target.has_dot("Flame Shock") and sb.flame_shock.ready:
        return sb.flame_shock
    return sb.lightning_bolt


def _for_encounters(
    name: str, description: str, function: RotationFunction, imbue: WeaponImbue
) -> list[Rotation]:
    """Register one rotation function for single target and leveling."""
    return [
        Rotation(
            display_name=name,
            description=description,
            encounter_type=kind,
            rotation_function=function,
            weapon_imbue=imbue,
        )
        for kind in (EncounterType.SINGLE_TARGET, EncounterType.MULTI_TARGET_LEVELING)
    ]


ROTATIONS: list[Rotation] = [
    *_for_encounters(
        "Stormstrike WF",
        "Stormstrike, Earth Shock, Maelstrom Lightning Bolt.",
        stormstrike,
        WeaponImbue.WINDFURY,
    ),
    *_for_encounters(
        "Shocks WF", "Searing Totem, Flame Shock, Earth Shock.", shocks, WeaponImbue.WINDFURY
    ),
    *_for_encounters(
        "Shocks RB", "Searing Totem, Flame Shock, Earth Shock.", shocks, WeaponImbue.ROCKBITER
    ),
    *_for_encounters("Caster FT", "Flame Shock, Lightning Bolt.", caster, WeaponImbue.FLAMETONGUE),
]
