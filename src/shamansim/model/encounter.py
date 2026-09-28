"""Encounter configuration."""

from dataclasses import dataclass

from shamansim.core.constants import MIN_LEVEL
from shamansim.core.enums import EncounterType, LevelDelta, Position


@dataclass(frozen=True, slots=True, kw_only=True)
class Encounter:
    """A fight to simulate.

    Single target / AoE: all enemies engage at once; the fight ends at `duration`
    or when every enemy dies. Leveling: pulls of `enemy_count` enemies repeat
    until `duration`, drinking between pulls when mana is below
    `drink_below_mana_pct`. `enemy_armor` reduces physical damage; `position`
    decides whether enemies can parry.
    """

    display_name: str
    description: str
    encounter_type: EncounterType
    duration: float
    enemy_count: int
    enemy_health: float
    enemy_armor: float = 0.0
    enemy_level_delta: LevelDelta = LevelDelta.SAME
    position: Position = Position.BEHIND
    drink_below_mana_pct: float = 50.0

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("duration must be positive")
        if self.enemy_count < 1:
            raise ValueError("enemy_count must be >= 1")
        if self.enemy_health <= 0:
            raise ValueError("enemy_health must be positive")
        if self.enemy_armor < 0:
            raise ValueError("enemy_armor must be >= 0")
        if not 0.0 <= self.drink_below_mana_pct <= 100.0:
            raise ValueError("drink_below_mana_pct must be in [0, 100]")

    def enemy_level(self, character_level: int) -> int:
        """Absolute enemy level."""
        return max(character_level + int(self.enemy_level_delta), MIN_LEVEL)
