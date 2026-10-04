"""Stat weights configuration."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Final


@dataclass(frozen=True, slots=True)
class StatInfo:
    """Display name, unit, and default simulated step of a stat."""

    name: str
    unit: str
    percent: bool
    default_step: float


class Stat(Enum):
    """Character-sheet stats that can be weighted."""

    ATTACK_POWER = StatInfo("Attack power", "point", percent=False, default_step=50)
    # 25 strength = 50 attack power, the attack power step.
    STRENGTH = StatInfo("Strength", "point", percent=False, default_step=25)
    AGILITY = StatInfo("Agility", "point", percent=False, default_step=20)
    SPELL_POWER = StatInfo("Spell power", "point", percent=False, default_step=50)
    INTELLECT = StatInfo("Intellect", "point", percent=False, default_step=20)
    SPIRIT = StatInfo("Spirit", "point", percent=False, default_step=20)
    MP5 = StatInfo("Mp5", "point", percent=False, default_step=10)
    WEAPON_SKILL = StatInfo("Weapon skill", "point", percent=False, default_step=5)
    MELEE_CRIT = StatInfo("Melee crit", "1%", percent=True, default_step=2)
    MELEE_HIT = StatInfo("Melee hit", "1%", percent=True, default_step=2)
    SPELL_CRIT = StatInfo("Spell crit", "1%", percent=True, default_step=2)
    SPELL_HIT = StatInfo("Spell hit", "1%", percent=True, default_step=2)

    @property
    def info(self) -> StatInfo:
        """Display name, unit, and default step."""
        value: StatInfo = self.value
        return value


REFERENCE_STAT: Final = Stat.ATTACK_POWER
"""Equivalence points are relative to one point of this stat."""

DEFAULT_STEPS: Final = {stat: stat.info.default_step for stat in Stat}


@dataclass(frozen=True, slots=True, kw_only=True)
class StatWeightsConfig:
    """One character + encounter + rotation + talents to compute stat weights for.

    `character`, `encounter`, and `rotation` are display names from the other
    configs (the rotation must match the encounter's type); `talents` is a
    Wowhead talent calculator link. Each stat in `steps` is raised by its step
    (in points, or percent for percent stats) and compared with the unmodified
    character over the same random numbers. `iterations` overrides
    `META.iterations` when set.
    """

    character: str
    encounter: str
    rotation: str
    talents: str
    iterations: int | None = None
    steps: dict[Stat, float] = field(default_factory=lambda: dict(DEFAULT_STEPS))

    def __post_init__(self) -> None:
        if self.iterations is not None and self.iterations < 2:
            raise ValueError("iterations must be >= 2")
        if REFERENCE_STAT not in self.steps:
            raise ValueError(f"steps must include {REFERENCE_STAT.name}: EP is relative to it")
        if any(step <= 0 for step in self.steps.values()):
            raise ValueError("steps must be positive")
        skill = self.steps.get(Stat.WEAPON_SKILL)
        if skill is not None and skill != int(skill):
            raise ValueError("the weapon skill step must be a whole number")
