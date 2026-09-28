"""Consumables (WoW Forever values from Wowhead)."""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class Drink:
    """A drink restoring mana linearly over its duration."""

    name: str
    mana: float
    duration: float
    required_level: int

    @property
    def mana_per_second(self) -> float:
        """Restore rate."""
        return self.mana / self.duration


class Water(Enum):
    """Selectable water; conjured and vendor waters share values per tier."""

    CONJURED_WATER = Drink("Conjured Water", 145.0, 18.0, 1)
    CONJURED_FRESH_WATER = Drink("Conjured Fresh Water", 420.0, 21.0, 5)
    CONJURED_PURIFIED_WATER = Drink("Conjured Purified Water", 803.0, 24.0, 15)
    REFRESHING_SPRING_WATER = Drink("Refreshing Spring Water", 145.0, 18.0, 1)
    ICE_COLD_MILK = Drink("Ice Cold Milk", 420.0, 21.0, 5)
    MELON_JUICE = Drink("Melon Juice", 803.0, 24.0, 15)
    SWEET_NECTAR = Drink("Sweet Nectar", 1293.0, 27.0, 25)
    MOONBERRY_JUICE = Drink("Moonberry Juice", 1915.0, 30.0, 35)

    @property
    def drink(self) -> Drink:
        """Drink stats."""
        value: Drink = self.value
        return value
