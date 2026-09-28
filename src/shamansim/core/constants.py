"""Game mechanics constants (Classic formulas via wowsims/classic)."""

from typing import Final

from shamansim.core.enums import LevelDelta

MIN_LEVEL: Final = 1
MAX_LEVEL: Final = 60

GCD_SECONDS: Final = 1.5

# --- Spells -----------------------------------------------------------------

# Spell hit table: base miss chance by enemy level delta, floored at 1%.
BASE_SPELL_MISS: Final[dict[LevelDelta, float]] = {
    LevelDelta.MINUS_3_OR_LESS: 0.01,
    LevelDelta.MINUS_2: 0.02,
    LevelDelta.MINUS_1: 0.03,
    LevelDelta.SAME: 0.04,
    LevelDelta.PLUS_1: 0.05,
    LevelDelta.PLUS_2: 0.06,
    LevelDelta.PLUS_3: 0.17,
}
MIN_SPELL_MISS: Final = 0.01

# Spell crit chance removed by higher-level enemies.
SPELL_CRIT_SUPPRESSION: Final[dict[LevelDelta, float]] = {
    LevelDelta.PLUS_2: 0.003,
    LevelDelta.PLUS_3: 0.021,
}
SPELL_CRIT_MULTIPLIER: Final = 1.5

# Average partial resist added per enemy level above the caster.
PARTIAL_RESIST_PER_LEVEL: Final = 0.02

# --- Melee (github.com/magey/classic-warrior/wiki/Attack-table) --------------

SKILL_PER_LEVEL: Final = 5
MELEE_BASE_MISS: Final = 0.05
MISS_PER_SKILL: Final = 0.001
MISS_PER_SKILL_LARGE_GAP: Final = 0.002
LARGE_SKILL_GAP: Final = 10
BASE_DODGE: Final = 0.05
DODGE_PER_SKILL: Final = 0.001
BASE_PARRY: Final = 0.05
PARRY_PER_SKILL: Final = 0.001
PARRY_PER_SKILL_LARGE_GAP: Final = 0.006
GLANCE_BASE: Final = 0.1
GLANCE_PER_DEFENSE: Final = 0.02
CRIT_SUPPRESSION_PER_DEFENSE: Final = 0.002
CRIT_SUPPRESSION_PER_DEFENSE_LOW: Final = 0.0004
CRIT_SUPPRESSION_PLUS_3: Final = 0.018
MELEE_CRIT_MULTIPLIER: Final = 2.0
ATTACK_POWER_PER_DPS: Final = 14.0

# Physical damage reduction: armor / (armor + 400 + 85 * attacker level).
ARMOR_BASE: Final = 400.0
ARMOR_PER_LEVEL: Final = 85.0

# --- Mana -------------------------------------------------------------------

# Spirit regen per second: (15 + Spirit / 5) per 2 s tick (wowsims default).
SPIRIT_REGEN_BASE_PER_SECOND: Final = 7.5
SPIRIT_REGEN_PER_SPIRIT_PER_SECOND: Final = 1.0 / 10.0
FIVE_SECOND_RULE_SECONDS: Final = 5.0
MP5_INTERVAL_SECONDS: Final = 5.0

# Mana from intellect: first 20 points give 1 mana each, the rest 15.
INTELLECT_MANA_THRESHOLD: Final = 20
MANA_PER_INTELLECT: Final = 15
