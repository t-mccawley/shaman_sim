"""Shared enumerations."""

from enum import IntEnum, StrEnum


class School(StrEnum):
    """Damage school."""

    PHYSICAL = "physical"
    NATURE = "nature"
    FIRE = "fire"
    FROST = "frost"


class TalentTree(StrEnum):
    """Shaman talent trees, in in-game order."""

    ELEMENTAL = "Elemental"
    ENHANCEMENT = "Enhancement"
    RESTORATION = "Restoration"


class EncounterType(StrEnum):
    """Encounter kind; rotations only run against encounters of the same type."""

    SINGLE_TARGET = "single_target"
    MULTI_TARGET_AOE = "multi_target_aoe"
    MULTI_TARGET_LEVELING = "multi_target_leveling"


class LevelDelta(IntEnum):
    """Enemy level relative to the character."""

    MINUS_3_OR_LESS = -3
    MINUS_2 = -2
    MINUS_1 = -1
    SAME = 0
    PLUS_1 = 1
    PLUS_2 = 2
    PLUS_3 = 3


class Position(StrEnum):
    """Where the character stands; enemies parry only from the front."""

    BEHIND = "behind"
    FRONT = "front"


class CastKind(StrEnum):
    """How a spell occupies the caster."""

    INSTANT = "instant"
    CAST = "cast"
    MELEE = "melee"
    TOTEM = "totem"
    BUFF = "buff"


class Targeting(StrEnum):
    """Which enemies a spell hits."""

    SINGLE = "single"
    AOE = "aoe"
    CHAIN = "chain"


class HitOutcome(StrEnum):
    """Result of an attack roll."""

    MISS = "miss"
    DODGE = "dodge"
    PARRY = "parry"
    GLANCE = "glance"
    HIT = "hit"
    CRIT = "crit"


class WeaponImbue(StrEnum):
    """Weapon enchant kept on the main hand for the whole encounter."""

    NONE = "None"
    ROCKBITER = "Rockbiter Weapon"
    FLAMETONGUE = "Flametongue Weapon"
    FROSTBRAND = "Frostbrand Weapon"
    WINDFURY = "Windfury Weapon"
