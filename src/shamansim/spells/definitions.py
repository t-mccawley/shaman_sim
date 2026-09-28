"""Spell and imbue data types.

`SpellRank` / `ImbueRank` hold values visible in game (configs/spellbook.py).
`SpellMechanics` holds fixed behaviour and coefficient scales (spells/mechanics.py).
"""

from dataclasses import dataclass
from enum import StrEnum

from shamansim.core.constants import MAX_LEVEL, MIN_LEVEL
from shamansim.core.enums import CastKind, School, Targeting, WeaponImbue


class SpellId(StrEnum):
    """Every simulated spell."""

    LIGHTNING_BOLT = "Lightning Bolt"
    CHAIN_LIGHTNING = "Chain Lightning"
    EARTH_SHOCK = "Earth Shock"
    FLAME_SHOCK = "Flame Shock"
    FROST_SHOCK = "Frost Shock"
    LAVA_BURST = "Lava Burst"
    FIRE_NOVA = "Fire Nova"
    STORMSTRIKE = "Stormstrike"
    SEARING_TOTEM = "Searing Totem"
    MAGMA_TOTEM = "Magma Totem"
    RAGE_OF_THE_FARSEER = "Rage of the Farseer"


@dataclass(frozen=True, slots=True, kw_only=True)
class DotData:
    """Periodic damage applied on hit, e.g. '28 Fire damage over 12 sec'."""

    damage: float
    duration: float
    ticks: int

    def __post_init__(self) -> None:
        if self.duration <= 0 or self.ticks < 1:
            raise ValueError("dot needs a positive duration and at least one tick")

    @property
    def tick_interval(self) -> float:
        """Seconds between ticks."""
        return self.duration / self.ticks

    @property
    def damage_per_tick(self) -> float:
        """Base damage of one tick."""
        return self.damage / self.ticks


@dataclass(frozen=True, slots=True, kw_only=True)
class TotemData:
    """A totem that attacks every `attack_interval` seconds for `duration`."""

    duration: float
    attack_interval: float

    def __post_init__(self) -> None:
        if self.duration <= 0 or self.attack_interval <= 0:
            raise ValueError("totem needs a positive duration and attack interval")


@dataclass(frozen=True, slots=True, kw_only=True)
class BuffData:
    """A self-buff, e.g. 'attack speed by 30% for 25 sec'."""

    duration: float
    attack_speed_pct: float = 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class SpellRank:
    """One learnable rank, as shown in game.

    Totems: min/max damage are per totem attack.
    """

    rank: int
    level: int
    min_damage: float = 0.0
    max_damage: float = 0.0
    mana_cost: float = 0.0
    base_mana_pct: float = 0.0
    cast_time: float = 0.0
    cooldown: float = 0.0
    dot: DotData | None = None
    totem: TotemData | None = None
    buff: BuffData | None = None
    wowhead_id: int | None = None
    confirmed_in_game_date: str | None = None

    def __post_init__(self) -> None:
        if not MIN_LEVEL <= self.level <= MAX_LEVEL:
            raise ValueError(f"rank {self.rank}: level {self.level} out of range")
        if self.min_damage > self.max_damage:
            raise ValueError(f"rank {self.rank}: min_damage exceeds max_damage")
        if min(self.mana_cost, self.base_mana_pct, self.cast_time, self.cooldown) < 0:
            raise ValueError(f"rank {self.rank}: negative cost, cast time, or cooldown")

    @property
    def average_damage(self) -> float:
        """Mean of the damage range."""
        return (self.min_damage + self.max_damage) / 2


@dataclass(frozen=True, slots=True, kw_only=True)
class ImbueRank:
    """One weapon imbue rank. `value` depends on the imbue:

    Rockbiter: attack power bonus. Flametongue: X in 'X / 100 * weapon speed'
    Fire damage per hit. Frostbrand: Frost damage per proc. Windfury: attack
    power bonus of each extra attack.
    """

    rank: int
    level: int
    value: float
    mana_cost: float = 0.0
    wowhead_id: int | None = None
    confirmed_in_game_date: str | None = None

    def __post_init__(self) -> None:
        if not MIN_LEVEL <= self.level <= MAX_LEVEL:
            raise ValueError(f"imbue rank {self.rank}: level {self.level} out of range")


@dataclass(frozen=True, slots=True, kw_only=True)
class SpellMechanics:
    """Fixed spell behaviour.

    `direct_scale` and `dot_scale` multiply the formula coefficient (coefficients.py).
    Spells sharing a `cooldown_group` share one cooldown (the Shocks).
    """

    spell_id: SpellId
    school: School
    cast_kind: CastKind
    targeting: Targeting
    direct_scale: float = 1.0
    dot_scale: float = 1.0
    scale_note: str = ""
    granted_by_talent: str | None = None
    cooldown_group: str | None = None
    weapon_damage: bool = False
    fire_totem: bool = False
    requires_fire_totem: bool = False
    chain_targets: int = 1
    chain_falloff: float = 1.0


@dataclass(frozen=True, slots=True)
class SpellDefinition:
    """A spell's mechanics plus its configured ranks (may be empty)."""

    mechanics: SpellMechanics
    ranks: tuple[SpellRank, ...]

    def __post_init__(self) -> None:
        numbers = [r.rank for r in self.ranks]
        if len(numbers) != len(set(numbers)):
            raise ValueError(f"{self.name}: duplicate rank numbers")
        if self.cast_kind is CastKind.TOTEM and any(r.totem is None for r in self.ranks):
            raise ValueError(f"{self.name}: totem ranks need totem data")
        if self.cast_kind is CastKind.BUFF and any(r.buff is None for r in self.ranks):
            raise ValueError(f"{self.name}: buff ranks need buff data")

    @property
    def spell_id(self) -> SpellId:
        """Identifier."""
        return self.mechanics.spell_id

    @property
    def name(self) -> str:
        """Display name."""
        return self.mechanics.spell_id.value

    @property
    def school(self) -> School:
        """Damage school."""
        return self.mechanics.school

    @property
    def cast_kind(self) -> CastKind:
        """How the spell occupies the caster."""
        return self.mechanics.cast_kind

    @property
    def targeting(self) -> Targeting:
        """Single target, AoE, or chain."""
        return self.mechanics.targeting

    def rank_for_level(self, level: int) -> SpellRank | None:
        """Highest rank learnable at `level`, if any."""
        known = [r for r in self.ranks if r.level <= level]
        return max(known, key=lambda r: r.rank) if known else None


type SpellCatalog = dict[SpellId, SpellDefinition]
"""Every spell with its configured ranks."""

type ImbueCatalog = dict[WeaponImbue, tuple[ImbueRank, ...]]
"""Every weapon imbue with its configured ranks."""


@dataclass(frozen=True, slots=True)
class Spellbook:
    """Configured spells and weapon imbues."""

    spells: SpellCatalog
    imbues: ImbueCatalog


def imbue_rank_for_level(ranks: tuple[ImbueRank, ...], level: int) -> ImbueRank | None:
    """Highest imbue rank learnable at `level`, if any."""
    known = [r for r in ranks if r.level <= level]
    return max(known, key=lambda r: r.rank) if known else None
