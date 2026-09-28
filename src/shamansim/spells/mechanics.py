"""Fixed spell mechanics, proc constants, and catalog assembly.

Scales marked "wowsims" are Blizzard's per-spell adjustments, fitted so the
calculated coefficients match wowsims/classic.
"""

from collections.abc import Mapping, Sequence
from typing import Final

from shamansim.core.enums import CastKind, School, Targeting, WeaponImbue
from shamansim.spells.coefficients import AOE_SCALE
from shamansim.spells.definitions import (
    ImbueCatalog,
    ImbueRank,
    SpellCatalog,
    SpellDefinition,
    SpellId,
    SpellMechanics,
    SpellRank,
)

SHOCK_COOLDOWN_GROUP: Final = "shock"

SPELL_MECHANICS: Final[dict[SpellId, SpellMechanics]] = {
    m.spell_id: m
    for m in (
        SpellMechanics(
            spell_id=SpellId.LIGHTNING_BOLT,
            school=School.NATURE,
            cast_kind=CastKind.CAST,
            targeting=Targeting.SINGLE,
        ),
        SpellMechanics(
            spell_id=SpellId.CHAIN_LIGHTNING,
            school=School.NATURE,
            cast_kind=CastKind.CAST,
            targeting=Targeting.CHAIN,
            chain_targets=3,
            chain_falloff=0.7,
        ),
        SpellMechanics(
            spell_id=SpellId.EARTH_SHOCK,
            school=School.NATURE,
            cast_kind=CastKind.INSTANT,
            targeting=Targeting.SINGLE,
            direct_scale=0.9,
            scale_note="wowsims",
            cooldown_group=SHOCK_COOLDOWN_GROUP,
        ),
        SpellMechanics(
            spell_id=SpellId.FLAME_SHOCK,
            school=School.FIRE,
            cast_kind=CastKind.INSTANT,
            targeting=Targeting.SINGLE,
            direct_scale=0.5,
            dot_scale=0.5,
            scale_note="wowsims (direct/DoT split)",
            cooldown_group=SHOCK_COOLDOWN_GROUP,
        ),
        SpellMechanics(
            spell_id=SpellId.FROST_SHOCK,
            school=School.FROST,
            cast_kind=CastKind.INSTANT,
            targeting=Targeting.SINGLE,
            direct_scale=0.9,
            scale_note="wowsims",
            cooldown_group=SHOCK_COOLDOWN_GROUP,
        ),
        SpellMechanics(
            spell_id=SpellId.LAVA_BURST,
            school=School.FIRE,
            cast_kind=CastKind.CAST,
            targeting=Targeting.SINGLE,
            scale_note="new in Forever; standard formula",
            granted_by_talent="Lava Burst",
        ),
        SpellMechanics(
            spell_id=SpellId.FIRE_NOVA,
            school=School.FIRE,
            cast_kind=CastKind.INSTANT,
            targeting=Targeting.AOE,
            direct_scale=AOE_SCALE,
            scale_note="AoE",
            requires_fire_totem=True,
        ),
        SpellMechanics(
            spell_id=SpellId.STORMSTRIKE,
            school=School.PHYSICAL,
            cast_kind=CastKind.MELEE,
            targeting=Targeting.SINGLE,
            scale_note="weapon damage",
            granted_by_talent="Stormstrike",
            weapon_damage=True,
        ),
        SpellMechanics(
            spell_id=SpellId.SEARING_TOTEM,
            school=School.FIRE,
            cast_kind=CastKind.TOTEM,
            targeting=Targeting.SINGLE,
            direct_scale=0.1162,
            scale_note="wowsims",
            fire_totem=True,
        ),
        SpellMechanics(
            spell_id=SpellId.MAGMA_TOTEM,
            school=School.FIRE,
            cast_kind=CastKind.TOTEM,
            targeting=Targeting.AOE,
            direct_scale=0.0578,
            scale_note="wowsims",
            fire_totem=True,
        ),
        SpellMechanics(
            spell_id=SpellId.RAGE_OF_THE_FARSEER,
            school=School.PHYSICAL,
            cast_kind=CastKind.BUFF,
            targeting=Targeting.SINGLE,
            granted_by_talent="Rage of the Farseer",
        ),
    )
}

# Stormstrike: next Lightning Bolt, Chain Lightning, or Earth Shock deals +20%.
STORMSTRIKE_BONUS: Final = 0.20
STORMSTRIKE_DURATION: Final = 12.0
STORMSTRIKE_EMPOWERS: Final = frozenset(
    {SpellId.LIGHTNING_BOLT, SpellId.CHAIN_LIGHTNING, SpellId.EARTH_SHOCK}
)

# Lava Burst deals +20% while Flame Shock is on the target.
LAVA_BURST_FLAME_SHOCK_BONUS: Final = 0.20

# Weapon imbues (Forever tooltips; proc details from wowsims/classic).
IMBUE_SCHOOLS: Final[dict[WeaponImbue, School]] = {
    WeaponImbue.FLAMETONGUE: School.FIRE,
    WeaponImbue.FROSTBRAND: School.FROST,
}
FLAMETONGUE_DAMAGE_DIVISOR: Final = 100.0
FROSTBRAND_PROCS_PER_MINUTE: Final = 9.0
WINDFURY_CHANCE: Final = 0.20
WINDFURY_EXTRA_ATTACKS: Final = 2
WINDFURY_COOLDOWN: Final = 1.5


def build_catalog(ranks: Mapping[SpellId, Sequence[SpellRank]]) -> SpellCatalog:
    """Combine mechanics with configured ranks; spells without ranks are never known."""
    return {
        spell_id: SpellDefinition(mechanics, tuple(ranks.get(spell_id, ())))
        for spell_id, mechanics in SPELL_MECHANICS.items()
    }


def build_imbue_catalog(ranks: Mapping[WeaponImbue, Sequence[ImbueRank]]) -> ImbueCatalog:
    """Configured imbue ranks for every imbue."""
    return {imbue: tuple(ranks.get(imbue, ())) for imbue in WeaponImbue}
