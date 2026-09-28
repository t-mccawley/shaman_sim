"""Rotation configuration."""

from collections.abc import Callable
from dataclasses import dataclass, field

from shamansim.core.enums import EncounterType, WeaponImbue
from shamansim.engine.state import SpellHandle
from shamansim.engine.views import SimState
from shamansim.spells.definitions import SpellId

type SpellChoice = SpellHandle | SpellId | None
"""A rotation's pick: a spell, or None to wait this tick."""

type RotationFunction = Callable[[SimState], SpellChoice]


@dataclass(frozen=True, slots=True, kw_only=True)
class Rotation:
    """A priority function called whenever the character is free to act.

    Melee auto attacks run on their own. `weapon_imbue` stays on the weapon for
    the whole encounter at its highest known rank. Spells cast at the highest
    rank known at the character's level unless `rank_overrides` pins a rank,
    e.g. {SpellId.LIGHTNING_BOLT: 1}.
    """

    display_name: str
    description: str
    encounter_type: EncounterType
    rotation_function: RotationFunction
    weapon_imbue: WeaponImbue = WeaponImbue.NONE
    rank_overrides: dict[SpellId, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if any(rank < 1 for rank in self.rank_overrides.values()):
            raise ValueError(f"{self.display_name}: rank overrides must be >= 1")
