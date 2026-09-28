"""Character configuration."""

from dataclasses import dataclass, field

from shamansim.core.constants import (
    INTELLECT_MANA_THRESHOLD,
    MANA_PER_INTELLECT,
    MAX_LEVEL,
    MIN_LEVEL,
    SKILL_PER_LEVEL,
)
from shamansim.core.enums import School
from shamansim.model.consumables import Water


@dataclass(frozen=True, slots=True, kw_only=True)
class SchoolValues:
    """A spell stat with a general value plus per-school bonuses."""

    general: float = 0.0
    nature: float = 0.0
    fire: float = 0.0
    frost: float = 0.0

    def for_school(self, school: School) -> float:
        """Total value for a school (general + school bonus)."""
        bonus = {
            School.NATURE: self.nature,
            School.FIRE: self.fire,
            School.FROST: self.frost,
            School.PHYSICAL: 0.0,
        }
        return self.general + bonus[school]


@dataclass(frozen=True, slots=True, kw_only=True)
class Weapon:
    """Main-hand weapon as shown on its tooltip."""

    name: str
    min_damage: float
    max_damage: float
    speed: float
    two_handed: bool = False

    def __post_init__(self) -> None:
        if self.min_damage > self.max_damage or self.speed <= 0:
            raise ValueError(f"{self.name}: invalid damage range or speed")

    @property
    def average_damage(self) -> float:
        """Mean base damage."""
        return (self.min_damage + self.max_damage) / 2


@dataclass(frozen=True, slots=True, kw_only=True)
class Character:
    """Character stats as shown in game, after gear and buffs.

    Percent stats are in percent (5.5 = 5.5%). `talents_on_sheet` is the talent
    calculator link active when the stats were copied; its stat bonuses
    (Thundering Strikes, Ancestral Knowledge, Mental Dexterity, Mental
    Quickness) are removed before each candidate's talents are applied.
    """

    display_name: str
    level: int
    intellect: float
    spirit: float
    mana: float
    mp5: float = 0.0
    attack_power: float = 0.0
    melee_crit: float = 0.0
    melee_hit: float = 0.0
    weapon_skill_bonus: int = 0
    spell_power: SchoolValues = field(default_factory=SchoolValues)
    spell_crit: SchoolValues = field(default_factory=SchoolValues)
    spell_hit: SchoolValues = field(default_factory=SchoolValues)
    weapon: Weapon
    water: Water = Water.CONJURED_WATER
    talents_on_sheet: str | None = None

    def __post_init__(self) -> None:
        if not MIN_LEVEL <= self.level <= MAX_LEVEL:
            raise ValueError(f"level must be in [{MIN_LEVEL}, {MAX_LEVEL}], got {self.level}")
        if self.mana <= 0:
            raise ValueError("mana must be positive")

    @property
    def weapon_skill(self) -> int:
        """Weapon skill (5 per level plus bonuses)."""
        return self.level * SKILL_PER_LEVEL + self.weapon_skill_bonus

    @property
    def base_mana(self) -> float:
        """Mana excluding intellect contribution."""
        return max(self.mana - mana_from_intellect(self.intellect), 0.0)


def mana_from_intellect(intellect: float) -> float:
    """Mana granted by intellect."""
    return min(intellect, INTELLECT_MANA_THRESHOLD) + MANA_PER_INTELLECT * max(
        intellect - INTELLECT_MANA_THRESHOLD, 0.0
    )
