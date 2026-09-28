"""Spell and melee attack tables (Classic formulas via wowsims/classic)."""

import random
from dataclasses import dataclass

from shamansim.core.constants import (
    ARMOR_BASE,
    ARMOR_PER_LEVEL,
    BASE_DODGE,
    BASE_PARRY,
    BASE_SPELL_MISS,
    CRIT_SUPPRESSION_PER_DEFENSE,
    CRIT_SUPPRESSION_PER_DEFENSE_LOW,
    CRIT_SUPPRESSION_PLUS_3,
    DODGE_PER_SKILL,
    GLANCE_BASE,
    GLANCE_PER_DEFENSE,
    LARGE_SKILL_GAP,
    MELEE_BASE_MISS,
    MIN_SPELL_MISS,
    MISS_PER_SKILL,
    MISS_PER_SKILL_LARGE_GAP,
    PARRY_PER_SKILL,
    PARRY_PER_SKILL_LARGE_GAP,
    PARTIAL_RESIST_PER_LEVEL,
    SKILL_PER_LEVEL,
    SPELL_CRIT_MULTIPLIER,
    SPELL_CRIT_SUPPRESSION,
)
from shamansim.core.enums import HitOutcome, LevelDelta, Position, School

_MAX_PARTIAL_RESIST = 0.75


def level_delta(character_level: int, enemy_level: int) -> LevelDelta:
    """Enemy-minus-character level, clamped to the LevelDelta range."""
    delta = enemy_level - character_level
    return LevelDelta(max(min(delta, LevelDelta.PLUS_3), LevelDelta.MINUS_3_OR_LESS))


def spell_hit_chance(delta: LevelDelta, hit_pct: float) -> float:
    """Chance a spell lands (before partial resists)."""
    miss = max(BASE_SPELL_MISS[delta] - hit_pct / 100.0, MIN_SPELL_MISS)
    return 1.0 - miss


def spell_crit_multiplier(crit_damage_bonus: float) -> float:
    """Spell crit multiplier; bonus scales the extra 50%."""
    return 1.0 + (SPELL_CRIT_MULTIPLIER - 1.0) * (1.0 + crit_damage_bonus)


@dataclass(frozen=True, slots=True)
class ResistTable:
    """Partial resist roll thresholds for 25/50/75% resists."""

    no_resist: float
    resist_25: float
    resist_50: float

    @classmethod
    def for_level_gap(cls, level_gap: int) -> "ResistTable":
        """Level-based partial resists against higher-level enemies."""
        coef = min(max(level_gap, 0) * PARTIAL_RESIST_PER_LEVEL / _MAX_PARTIAL_RESIST, 1.0)
        val = coef * 3.0
        if val <= 1.0:
            return cls(0.76 * val, 0.21 * val, 0.03 * val)
        if val <= 2.0:
            val -= 1.0
            return cls(0.76 + 0.24 * val, 0.21 + 0.57 * val, 0.03 + 0.19 * val)
        val -= 2.0
        return cls(1.0, 0.78 + 0.18 * val, 0.22 + 0.58 * val)

    def roll_multiplier(self, rng: random.Random) -> float:
        """Random damage multiplier after partial resists."""
        if self.no_resist <= 0.0:
            return 1.0
        roll = rng.random()
        if roll > self.no_resist:
            return 1.0
        if roll > self.resist_25:
            return 0.75
        if roll > self.resist_50:
            return 0.5
        return 0.25


@dataclass(frozen=True, slots=True)
class SpellProfile:
    """Precomputed spell numbers for one school against one enemy level."""

    hit_chance: float
    crit_chance: float
    crit_multiplier: float
    spell_power: float

    def roll(self, rng: random.Random, bonus_crit: float = 0.0) -> HitOutcome:
        """Roll miss, then crit."""
        if rng.random() >= self.hit_chance:
            return HitOutcome.MISS
        if rng.random() < self.crit_chance + bonus_crit:
            return HitOutcome.CRIT
        return HitOutcome.HIT


def spell_profile(
    school: School,
    *,
    delta: LevelDelta,
    hit_pct: float,
    crit_pct: float,
    crit_damage_bonus: float,
    spell_power: float,
) -> SpellProfile:
    """Combine stats for one magic school."""
    crit = max(crit_pct / 100.0 - SPELL_CRIT_SUPPRESSION.get(delta, 0.0), 0.0)
    return SpellProfile(
        hit_chance=spell_hit_chance(delta, hit_pct),
        crit_chance=min(crit, 1.0),
        crit_multiplier=spell_crit_multiplier(crit_damage_bonus),
        spell_power=spell_power,
    )


@dataclass(frozen=True, slots=True)
class MeleeTable:
    """Melee attack table against one enemy.

    Chances are fractions. Crit chance excludes temporary bonuses, which are
    passed to the rolls.
    """

    miss: float
    dodge: float
    parry: float
    glance: float
    glance_min: float
    glance_max: float
    crit: float
    armor_multiplier: float

    @classmethod
    def build(
        cls,
        *,
        level: int,
        enemy_level: int,
        weapon_skill: int,
        hit_pct: float,
        crit_pct: float,
        enemy_armor: float,
        position: Position,
    ) -> "MeleeTable":
        """Classic attack table for `level` attacking `enemy_level`."""
        defense = enemy_level * SKILL_PER_LEVEL
        gap = defense - weapon_skill
        base_gap = defense - level * SKILL_PER_LEVEL
        if gap > LARGE_SKILL_GAP:
            miss = MELEE_BASE_MISS + gap * MISS_PER_SKILL_LARGE_GAP
            hit = max(hit_pct / 100.0 - (gap - LARGE_SKILL_GAP) * MISS_PER_SKILL_LARGE_GAP, 0.0)
        else:
            miss = MELEE_BASE_MISS + gap * MISS_PER_SKILL
            hit = hit_pct / 100.0
        if base_gap > LARGE_SKILL_GAP:
            parry = BASE_PARRY + base_gap * PARRY_PER_SKILL_LARGE_GAP
        else:
            parry = BASE_PARRY + base_gap * PARRY_PER_SKILL
        suppression = (
            base_gap * CRIT_SUPPRESSION_PER_DEFENSE
            if base_gap > 0
            else base_gap * CRIT_SUPPRESSION_PER_DEFENSE_LOW
        )
        if enemy_level - level >= LevelDelta.PLUS_3:
            suppression += CRIT_SUPPRESSION_PLUS_3
        armor = enemy_armor / (enemy_armor + ARMOR_BASE + ARMOR_PER_LEVEL * level)
        return cls(
            miss=max(miss - hit, 0.0),
            dodge=max(BASE_DODGE + gap * DODGE_PER_SKILL, 0.0),
            parry=max(parry, 0.0) if position is Position.FRONT else 0.0,
            glance=max(GLANCE_BASE + base_gap * GLANCE_PER_DEFENSE, 0.0),
            glance_min=max(min(1.3 - 0.05 * gap, 0.91), 0.01),
            glance_max=max(min(1.2 - 0.03 * gap, 0.99), 0.2),
            crit=max(crit_pct / 100.0 - suppression, 0.0),
            armor_multiplier=1.0 - armor,
        )

    def roll_auto(self, rng: random.Random, bonus_crit: float = 0.0) -> HitOutcome:
        """One-roll table for white swings: miss, dodge, parry, glance, crit, hit."""
        roll = rng.random()
        for chance, outcome in (
            (self.miss, HitOutcome.MISS),
            (self.dodge, HitOutcome.DODGE),
            (self.parry, HitOutcome.PARRY),
            (self.glance, HitOutcome.GLANCE),
            (self.crit + bonus_crit, HitOutcome.CRIT),
        ):
            if roll < chance:
                return outcome
            roll -= chance
        return HitOutcome.HIT

    def roll_special(self, rng: random.Random, bonus_crit: float = 0.0) -> HitOutcome:
        """Special attacks: miss, dodge, parry, then a separate crit roll."""
        roll = rng.random()
        for chance, outcome in (
            (self.miss, HitOutcome.MISS),
            (self.dodge, HitOutcome.DODGE),
            (self.parry, HitOutcome.PARRY),
        ):
            if roll < chance:
                return outcome
            roll -= chance
        return HitOutcome.CRIT if rng.random() < self.crit + bonus_crit else HitOutcome.HIT

    def glance_multiplier(self, rng: random.Random) -> float:
        """Damage multiplier of a glancing blow."""
        return rng.uniform(self.glance_min, self.glance_max)
