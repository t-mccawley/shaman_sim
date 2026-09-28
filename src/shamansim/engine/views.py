"""Read-only views passed to rotation functions."""

from collections.abc import Mapping

from shamansim.engine.state import CasterState, Enemy, SpellHandle
from shamansim.spells.definitions import SpellId


class SpellBook:
    """All spells, e.g. `spells.stormstrike.ready`."""

    __slots__ = ("_handles",)

    def __init__(self, handles: Mapping[SpellId, SpellHandle]) -> None:
        self._handles = dict(handles)

    def __getitem__(self, spell_id: SpellId) -> SpellHandle:
        return self._handles[spell_id]

    def all(self) -> tuple[SpellHandle, ...]:
        """Every spell handle."""
        return tuple(self._handles.values())

    @property
    def lightning_bolt(self) -> SpellHandle:
        """Lightning Bolt."""
        return self._handles[SpellId.LIGHTNING_BOLT]

    @property
    def chain_lightning(self) -> SpellHandle:
        """Chain Lightning."""
        return self._handles[SpellId.CHAIN_LIGHTNING]

    @property
    def earth_shock(self) -> SpellHandle:
        """Earth Shock (shares the Shock cooldown)."""
        return self._handles[SpellId.EARTH_SHOCK]

    @property
    def flame_shock(self) -> SpellHandle:
        """Flame Shock (shares the Shock cooldown)."""
        return self._handles[SpellId.FLAME_SHOCK]

    @property
    def frost_shock(self) -> SpellHandle:
        """Frost Shock (shares the Shock cooldown)."""
        return self._handles[SpellId.FROST_SHOCK]

    @property
    def lava_burst(self) -> SpellHandle:
        """Lava Burst (talent)."""
        return self._handles[SpellId.LAVA_BURST]

    @property
    def fire_nova(self) -> SpellHandle:
        """Fire Nova (needs an active fire totem)."""
        return self._handles[SpellId.FIRE_NOVA]

    @property
    def stormstrike(self) -> SpellHandle:
        """Stormstrike (talent)."""
        return self._handles[SpellId.STORMSTRIKE]

    @property
    def searing_totem(self) -> SpellHandle:
        """Searing Totem (fire totem)."""
        return self._handles[SpellId.SEARING_TOTEM]

    @property
    def magma_totem(self) -> SpellHandle:
        """Magma Totem (fire totem)."""
        return self._handles[SpellId.MAGMA_TOTEM]

    @property
    def rage_of_the_farseer(self) -> SpellHandle:
        """Rage of the Farseer (talent)."""
        return self._handles[SpellId.RAGE_OF_THE_FARSEER]


class TargetView:
    """Read-only view of an enemy."""

    __slots__ = ("_caster", "_enemy")

    def __init__(self, enemy: Enemy, caster: CasterState) -> None:
        self._enemy = enemy
        self._caster = caster

    @property
    def health(self) -> float:
        """Current health."""
        return self._enemy.health

    @property
    def max_health(self) -> float:
        """Maximum health."""
        return self._enemy.max_health

    @property
    def health_pct(self) -> float:
        """Health in percent (0-100)."""
        return 100.0 * self._enemy.health / self._enemy.max_health

    @property
    def level(self) -> int:
        """Absolute level."""
        return self._enemy.level

    @property
    def stormstruck(self) -> bool:
        """True while Stormstrike empowers the next Lightning Bolt, Chain Lightning, Earth Shock."""
        return self._caster.time < self._enemy.stormstrike_until

    def has_dot(self, source: str) -> bool:
        """True if a DoT from `source` (e.g. 'Flame Shock') is ticking."""
        return source in self._enemy.dots


class SimState:
    """Everything a rotation may inspect at the current tick."""

    __slots__ = ("_caster", "_enemies", "spells")

    def __init__(self, caster: CasterState, spells: SpellBook, enemies: list[Enemy]) -> None:
        self._caster = caster
        self._enemies = enemies
        self.spells = spells

    @property
    def time(self) -> float:
        """Seconds since the encounter started."""
        return self._caster.time

    @property
    def mana(self) -> float:
        """Current mana."""
        return self._caster.mana

    @property
    def max_mana(self) -> float:
        """Maximum mana."""
        return self._caster.max_mana

    @property
    def mana_pct(self) -> float:
        """Mana in percent (0-100)."""
        return 100.0 * self._caster.mana / self._caster.max_mana

    @property
    def clearcasting(self) -> bool:
        """True if the next damage spell is free (Elemental Focus)."""
        return self._caster.clearcasting

    @property
    def maelstrom_stacks(self) -> int:
        """Active Maelstrom Weapon stacks."""
        return self._caster.active_maelstrom_stacks

    @property
    def flurry_charges(self) -> int:
        """Remaining Flurry swings."""
        return self._caster.flurry_charges

    @property
    def fire_totem(self) -> SpellId | None:
        """Active fire totem, if any."""
        return self._caster.active_fire_totem

    @property
    def fire_totem_remaining(self) -> float:
        """Seconds left on the active fire totem."""
        return max(self._caster.fire_totem_until - self._caster.time, 0.0)

    @property
    def enemies(self) -> tuple[TargetView, ...]:
        """Living enemies."""
        return tuple(TargetView(e, self._caster) for e in self._enemies if e.alive)

    @property
    def enemy_count(self) -> int:
        """Number of living enemies."""
        return sum(1 for e in self._enemies if e.alive)

    @property
    def target(self) -> TargetView | None:
        """Current target (first living enemy)."""
        alive = next((e for e in self._enemies if e.alive), None)
        return TargetView(alive, self._caster) if alive else None
