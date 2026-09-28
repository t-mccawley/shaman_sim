"""Runtime state and the spell handles given to rotation functions."""

from dataclasses import dataclass, field

from shamansim.core.enums import CastKind, School
from shamansim.spells.definitions import SpellDefinition, SpellId, SpellRank


@dataclass(slots=True, kw_only=True)
class CasterState:
    """Mutable caster state."""

    time: float = 0.0
    mana: float
    max_mana: float
    maelstrom_per_stack: float = 0.0
    busy_until: float = 0.0
    gcd_until: float = 0.0
    five_second_rule_until: float = 0.0
    drinking_until: float = 0.0
    clearcasting: bool = False
    cooldowns: dict[str, float] = field(default_factory=dict)
    flurry_charges: int = 0
    maelstrom_stacks: int = 0
    maelstrom_until: float = 0.0
    attack_speed_until: float = 0.0
    attack_speed_bonus: float = 0.0
    devastation_until: float = 0.0
    casting_regen_until: float = 0.0
    windfury_ready_at: float = 0.0
    fire_totem: SpellId | None = None
    fire_totem_until: float = 0.0

    @property
    def idle(self) -> bool:
        """True when a new action can start."""
        return self.time >= max(self.busy_until, self.gcd_until, self.drinking_until)

    @property
    def casting(self) -> bool:
        """True during a cast (melee swings wait)."""
        return self.time < self.busy_until

    @property
    def active_maelstrom_stacks(self) -> int:
        """Maelstrom Weapon stacks that have not expired."""
        return self.maelstrom_stacks if self.time < self.maelstrom_until else 0

    @property
    def active_fire_totem(self) -> SpellId | None:
        """Fire totem currently summoned, if any."""
        return self.fire_totem if self.time < self.fire_totem_until else None


@dataclass(slots=True, kw_only=True)
class DotState:
    """A periodic effect ticking on an enemy."""

    source: str
    tick_damage: float
    ticks_left: int
    tick_interval: float


@dataclass(slots=True, kw_only=True)
class Enemy:
    """Mutable enemy state."""

    index: int
    level: int
    max_health: float
    health: float
    stormstrike_until: float = 0.0
    dots: dict[str, DotState] = field(default_factory=dict)

    @property
    def alive(self) -> bool:
        """True while health remains."""
        return self.health > 0.0


class UnavailableSpellError(Exception):
    """A rotation used a spell the character cannot have; the candidate is invalid."""

    def __init__(self, spell: str, reason: str) -> None:
        super().__init__(f"rotation uses {spell}, which {reason}")
        self.spell = spell
        self.reason = reason


class SpellHandle:
    """A spell as seen by a rotation: static data plus live cooldown and cost.

    For a spell the character cannot have, only identity and `known` may be read;
    anything else raises UnavailableSpellError.
    """

    __slots__ = (
        "_base_cost",
        "_cast_time",
        "_caster",
        "_cooldown",
        "_rank",
        "cooldown_key",
        "definition",
        "unavailable_reason",
    )

    def __init__(
        self,
        definition: SpellDefinition,
        rank: SpellRank | None,
        caster: CasterState,
        *,
        unavailable_reason: str | None,
        cast_time: float,
        cooldown: float,
        base_cost: float,
    ) -> None:
        self.definition = definition
        self.unavailable_reason = unavailable_reason
        self.cooldown_key = definition.mechanics.cooldown_group or definition.name
        self._rank = rank
        self._cast_time = cast_time
        self._cooldown = cooldown
        self._base_cost = base_cost
        self._caster = caster

    def __repr__(self) -> str:
        rank = self._rank.rank if self._rank else None
        return f"SpellHandle({self.name}, rank={rank})"

    def _require(self) -> SpellRank:
        if self._rank is None:
            raise UnavailableSpellError(self.name, self.unavailable_reason or "is not known")
        return self._rank

    @property
    def spell_id(self) -> SpellId:
        """Spell identifier."""
        return self.definition.spell_id

    @property
    def name(self) -> str:
        """Display name."""
        return self.definition.name

    @property
    def school(self) -> School:
        """Damage school."""
        return self.definition.school

    @property
    def known(self) -> bool:
        """True if learned (level and talents allow it). Safe to read for any spell."""
        return self._rank is not None

    @property
    def rank(self) -> SpellRank:
        """Rank that will be cast."""
        return self._require()

    @property
    def _maelstrom_reduction(self) -> float:
        if self.spell_id is not SpellId.LIGHTNING_BOLT:
            return 0.0
        return self._caster.maelstrom_per_stack * self._caster.active_maelstrom_stacks

    @property
    def cast_time(self) -> float:
        """Cast time after talents and Maelstrom Weapon."""
        self._require()
        return self._cast_time * (1.0 - self._maelstrom_reduction)

    @property
    def cooldown(self) -> float:
        """Cooldown after talents."""
        self._require()
        return self._cooldown

    @property
    def cooldown_remaining(self) -> float:
        """Seconds until off cooldown (shared by the Shocks)."""
        self._require()
        return max(self._caster.cooldowns.get(self.cooldown_key, 0.0) - self._caster.time, 0.0)

    @property
    def on_cooldown(self) -> bool:
        """True while on cooldown."""
        return self.cooldown_remaining > 0.0

    @property
    def mana_cost(self) -> float:
        """Current cost including Clearcasting and Maelstrom Weapon."""
        self._require()
        if self._caster.clearcasting and self.definition.cast_kind is not CastKind.BUFF:
            return 0.0
        return self._base_cost * (1.0 - self._maelstrom_reduction)

    @property
    def affordable(self) -> bool:
        """True if current mana covers the cost."""
        return self._caster.mana >= self.mana_cost

    @property
    def ready(self) -> bool:
        """True if off cooldown and affordable."""
        return not self.on_cooldown and self.affordable
