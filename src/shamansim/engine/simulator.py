"""Discrete-tick encounter simulator with melee swings and spells."""

import heapq
import itertools
import math
import random
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

import numpy as np

from shamansim.core.constants import (
    ATTACK_POWER_PER_DPS,
    FIVE_SECOND_RULE_SECONDS,
    GCD_SECONDS,
    MELEE_CRIT_MULTIPLIER,
    MP5_INTERVAL_SECONDS,
    SPIRIT_REGEN_BASE_PER_SECOND,
    SPIRIT_REGEN_PER_SPIRIT_PER_SECOND,
)
from shamansim.core.enums import (
    CastKind,
    EncounterType,
    HitOutcome,
    School,
    Targeting,
    WeaponImbue,
)
from shamansim.engine.combat import (
    MeleeTable,
    ResistTable,
    SpellProfile,
    level_delta,
    spell_profile,
)
from shamansim.engine.results import IterationResult, dps_series, peak_dps
from shamansim.engine.state import (
    CasterState,
    DotState,
    Enemy,
    SpellHandle,
    UnavailableSpellError,
)
from shamansim.engine.views import SimState, SpellBook
from shamansim.model.character import Character
from shamansim.model.encounter import Encounter
from shamansim.model.rotation import Rotation
from shamansim.model.stats import EffectiveStats
from shamansim.spells.availability import resolve_imbue, resolve_rank
from shamansim.spells.coefficients import IMBUE_PROC_COEFFICIENT, RankCoefficients, calculate
from shamansim.spells.definitions import (
    ImbueCatalog,
    ImbueRank,
    Spellbook,
    SpellDefinition,
    SpellId,
    SpellRank,
)
from shamansim.spells.mechanics import (
    FLAMETONGUE_DAMAGE_DIVISOR,
    FROSTBRAND_PROCS_PER_MINUTE,
    LAVA_BURST_FLAME_SHOCK_BONUS,
    STORMSTRIKE_BONUS,
    STORMSTRIKE_DURATION,
    STORMSTRIKE_EMPOWERS,
    WINDFURY_CHANCE,
    WINDFURY_COOLDOWN,
    WINDFURY_EXTRA_ATTACKS,
)
from shamansim.talents.build import TalentBuild
from shamansim.talents.effects import TalentModifiers

MELEE: Final = "Melee"
WINDFURY_ATTACK: Final = "Windfury Attack"
LIGHTNING_OVERLOAD: Final = "Lightning Overload"
LIGHTNING_OVERLOAD_DAMAGE: Final = 0.5
OVERLOADING: Final = frozenset({SpellId.LIGHTNING_BOLT, SpellId.CHAIN_LIGHTNING})
FLURRY_CHARGES: Final = 3
DEVASTATION_DURATION: Final = 10.0
IMPROVED_STORMSTRIKE_REGEN: Final = 0.5
IMPROVED_STORMSTRIKE_DURATION: Final = 15.0
# ESTIMATED: Maelstrom Weapon proc rate is not stated; Season of Discovery used 10 PPM.
MAELSTROM_PROCS_PER_MINUTE: Final = 10.0
MAELSTROM_MAX_STACKS: Final = 5
MAELSTROM_DURATION: Final = 30.0
SECONDS_PER_MINUTE: Final = 60.0


class RejectReason:
    """Why a rotation's pick could not be cast."""

    COOLDOWN = "on cooldown"
    MANA = "not enough mana"
    NO_TARGET = "no target"
    NO_FIRE_TOTEM = "no fire totem"


def _cast_label(handle: SpellHandle) -> str:
    """Cast counter key, e.g. 'Lightning Bolt (Rank 4)'."""
    return f"{handle.name} (Rank {handle.rank.rank})"


@dataclass(frozen=True, slots=True)
class _SpellSetup:
    """Per-candidate static data for one spell."""

    definition: SpellDefinition
    rank: SpellRank | None
    unavailable_reason: str | None
    coefficients: RankCoefficients | None
    cast_time: float
    cooldown: float
    base_cost: float
    bonus_crit: float
    damage_multiplier: float


class Simulation:
    """A candidate (character + encounter + talents + rotation) ready to run."""

    def __init__(
        self,
        character: Character,
        encounter: Encounter,
        talents: TalentBuild,
        rotation: Rotation,
        spellbook: Spellbook,
        *,
        tick_seconds: float,
        peak_warmup_seconds: float,
    ) -> None:
        self.character = character
        self.encounter = encounter
        self.rotation = rotation
        self.tick_seconds = tick_seconds
        self.peak_warmup_seconds = peak_warmup_seconds
        self.modifiers = TalentModifiers.from_build(talents)
        self.stats = EffectiveStats.build(character, talents)
        self.enemy_level = encounter.enemy_level(character.level)
        self.resist_table = ResistTable.for_level_gap(self.enemy_level - character.level)
        self.imbue = self._resolve_imbue(spellbook.imbues)
        self.attack_power = self.stats.attack_power
        if rotation.weapon_imbue is WeaponImbue.ROCKBITER and self.imbue is not None:
            self.attack_power += self.imbue.value * self.modifiers.rockbiter_multiplier
        self.melee = MeleeTable.build(
            level=character.level,
            enemy_level=self.enemy_level,
            weapon_skill=character.weapon_skill,
            hit_pct=self.stats.melee_hit + self.modifiers.hit_pct,
            crit_pct=self.stats.melee_crit,
            enemy_armor=encounter.enemy_armor,
            position=encounter.position,
        )
        delta = level_delta(character.level, self.enemy_level)
        self.profiles: dict[School, SpellProfile] = {
            school: spell_profile(
                school,
                delta=delta,
                hit_pct=self.stats.spell_hit.for_school(school) + self.modifiers.hit_pct,
                crit_pct=self.stats.spell_crit.for_school(school),
                crit_damage_bonus=self.modifiers.spell_crit_damage_bonus.get(school, 0.0),
                spell_power=self.stats.spell_power.for_school(school),
            )
            for school in (School.NATURE, School.FIRE, School.FROST)
        }
        self.spells = {spell_id: self._setup(d) for spell_id, d in spellbook.spells.items()}

    def _resolve_imbue(self, imbues: ImbueCatalog) -> ImbueRank | None:
        imbue = self.rotation.weapon_imbue
        if imbue is WeaponImbue.NONE:
            return None
        resolution = resolve_imbue(imbue, imbues[imbue], self.character.level)
        if resolution.rank is None:
            raise ValueError(f"{imbue.value} {resolution.reason}")
        return resolution.rank

    def _setup(self, definition: SpellDefinition) -> _SpellSetup:
        mods = self.modifiers
        spell_id = definition.spell_id
        resolution = resolve_rank(
            definition,
            self.character.level,
            mods.granted_spells,
            self.rotation.rank_overrides.get(spell_id),
        )
        rank = resolution.rank
        if rank is None:
            return _SpellSetup(definition, None, resolution.reason, None, 0.0, 0.0, 0.0, 0.0, 1.0)
        cost = rank.mana_cost + rank.base_mana_pct / 100.0 * self.stats.base_mana
        cost *= mods.cost_multiplier_spell.get(spell_id, 1.0)
        return _SpellSetup(
            definition=definition,
            rank=rank,
            unavailable_reason=None,
            coefficients=calculate(definition.mechanics, rank),
            cast_time=max(rank.cast_time - mods.cast_time_reduction.get(spell_id, 0.0), 0.0),
            cooldown=max(rank.cooldown - mods.cooldown_reduction.get(spell_id, 0.0), 0.0),
            base_cost=cost,
            bonus_crit=mods.crit_pct_spell.get(spell_id, 0.0) / 100.0,
            damage_multiplier=mods.damage_multiplier_spell.get(spell_id, 1.0),
        )

    def weapon_damage(self, rng: random.Random, attack_power: float) -> float:
        """Weapon roll plus attack power (AP / 14 per second of weapon speed)."""
        weapon = self.character.weapon
        return rng.uniform(weapon.min_damage, weapon.max_damage) + (
            weapon.speed * attack_power / ATTACK_POWER_PER_DPS
        )

    def run(self, rng: random.Random) -> IterationResult:
        """Simulate one iteration."""
        return _Iteration(self, rng).run()


class _Iteration:
    """Mutable state for one run of a Simulation."""

    def __init__(self, sim: Simulation, rng: random.Random) -> None:
        self.sim = sim
        self.rng = rng
        self.dt = sim.tick_seconds
        self.end_tick = self._ticks(sim.encounter.duration)
        self.tick = 0
        self.caster = CasterState(
            mana=sim.stats.mana,
            max_mana=sim.stats.mana,
            maelstrom_per_stack=sim.modifiers.maelstrom_per_stack,
        )
        self.handles = {
            spell_id: SpellHandle(
                s.definition,
                s.rank,
                self.caster,
                unavailable_reason=s.unavailable_reason,
                cast_time=s.cast_time,
                cooldown=s.cooldown,
                base_cost=s.base_cost,
            )
            for spell_id, s in sim.spells.items()
        }
        self.enemies: list[Enemy] = []
        self.state = SimState(self.caster, SpellBook(self.handles), self.enemies)
        self.events: list[tuple[int, int, Callable[[], None]]] = []
        self.sequence = itertools.count()
        self.action_id = 0
        self.swing_id = 0
        self.totem_id = 0
        self.pull_active = False
        self.fight_over = False
        self.finished_tick = self.end_tick
        self.mana_synced_at = 0.0
        self.drink_started = 0.0
        self.damage = np.zeros(self.end_tick + 1, dtype=np.float64)
        self.damage_by_source: defaultdict[str, float] = defaultdict(float)
        self.casts: Counter[str] = Counter()
        self.blocked: defaultdict[str, float] = defaultdict(float)
        self.kills = 0
        self.drinking_time = 0.0
        self.mp5_rate = sim.character.mp5 / MP5_INTERVAL_SECONDS
        self.spirit_rate = (
            SPIRIT_REGEN_BASE_PER_SECOND + sim.character.spirit * SPIRIT_REGEN_PER_SPIRIT_PER_SECOND
        )

    # --- time ---------------------------------------------------------------

    def _ticks(self, seconds: float) -> int:
        return max(round(seconds / self.dt), 0)

    def _at(self, tick: int) -> float:
        return tick * self.dt

    def _schedule(self, delay: float, action: Callable[[], None]) -> None:
        heapq.heappush(self.events, (self.tick + self._ticks(delay), next(self.sequence), action))

    # --- main loop ----------------------------------------------------------

    def run(self) -> IterationResult:
        self._spawn_pull()
        while self.tick <= self.end_tick and not self.fight_over:
            self.caster.time = self._at(self.tick)
            self._sync_mana()
            while self.events and self.events[0][0] <= self.tick:
                heapq.heappop(self.events)[2]()
                self._check_pull_cleared()
                if self.fight_over:
                    break
            if self.fight_over:
                break
            waiting = self.pull_active and self.caster.idle
            if waiting:
                self._act()
                self._check_pull_cleared()
            next_tick = self.events[0][0] if self.events else self.end_tick + 1
            if self.pull_active:
                next_tick = min(next_tick, self._next_free_tick())
            self.tick = next_tick
        return self._result()

    def _next_free_tick(self) -> int:
        """Next tick the character can act (polls every tick while idle)."""
        c = self.caster
        free = self._ticks(max(c.busy_until, c.gcd_until, c.drinking_until))
        return max(free, self.tick + 1)

    def _result(self) -> IterationResult:
        end = min(self.finished_tick, self.end_tick)
        series = dps_series(self.damage, self.dt, end)
        elapsed = max(end, 1) * self.dt
        total = float(self.damage[: end + 1].sum())
        return IterationResult(
            total_dps=total / elapsed,
            peak_dps=peak_dps(series, self._ticks(self.sim.peak_warmup_seconds)),
            dps_series=series,
            elapsed=elapsed,
            damage_by_source=dict(self.damage_by_source),
            casts=dict(self.casts),
            blocked_seconds=dict(self.blocked),
            enemies_killed=self.kills,
            drinking_time=self.drinking_time,
        )

    # --- encounter flow -----------------------------------------------------

    def _spawn_pull(self) -> None:
        enc = self.sim.encounter
        self.enemies[:] = [
            Enemy(
                index=i,
                level=self.sim.enemy_level,
                max_health=enc.enemy_health,
                health=enc.enemy_health,
            )
            for i in range(enc.enemy_count)
        ]
        self.pull_active = True
        self.swing_id += 1
        swing = self.swing_id
        self._schedule(0.0, lambda: self._swing(swing))

    def _check_pull_cleared(self) -> None:
        if not self.pull_active or any(e.alive for e in self.enemies):
            return
        self.pull_active = False
        self.action_id += 1
        self.swing_id += 1
        self.caster.busy_until = self.caster.time
        if self.sim.encounter.encounter_type is not EncounterType.MULTI_TARGET_LEVELING:
            self.fight_over = True
            self.finished_tick = self.tick
            return
        if self.state.mana_pct < self.sim.encounter.drink_below_mana_pct:
            self._start_drinking()
        else:
            self._spawn_pull()

    def _start_drinking(self) -> None:
        caster = self.caster
        drink_rate = self.sim.character.water.drink.mana_per_second
        deficit = caster.max_mana - caster.mana
        base_rate = drink_rate + self.mp5_rate
        pre_spirit = max(caster.five_second_rule_until - caster.time, 0.0)
        if base_rate * pre_spirit >= deficit:
            duration = deficit / base_rate
        else:
            duration = pre_spirit + (deficit - base_rate * pre_spirit) / (
                base_rate + self.spirit_rate
            )
        ticks = max(math.ceil(duration / self.dt - 1e-9), 1)
        self.drink_started = caster.time
        caster.drinking_until = self._at(self.tick + ticks)
        self.drinking_time += ticks * self.dt
        heapq.heappush(self.events, (self.tick + ticks, next(self.sequence), self._spawn_pull))

    # --- mana ---------------------------------------------------------------

    def _casting_regen(self) -> float:
        """Fraction of spirit regen that continues inside the five-second rule."""
        improved = (
            IMPROVED_STORMSTRIKE_REGEN
            if self.caster.time < self.caster.casting_regen_until
            else 0.0
        )
        return max(self.sim.modifiers.casting_regen, improved)

    def _sync_mana(self) -> None:
        caster = self.caster
        start, now = self.mana_synced_at, caster.time
        if now <= start:
            return
        gain = self.mp5_rate * (now - start)
        outside = max(now - max(start, caster.five_second_rule_until), 0.0)
        inside = (now - start) - outside
        gain += self.spirit_rate * (outside + inside * self._casting_regen())
        drink_end = min(now, caster.drinking_until)
        drink_start = max(start, self.drink_started)
        if drink_end > drink_start:
            gain += self.sim.character.water.drink.mana_per_second * (drink_end - drink_start)
        caster.mana = min(caster.mana + gain, caster.max_mana)
        self.mana_synced_at = now

    def _spend(self, handle: SpellHandle) -> bool:
        """Pay for a cast; False if mana is short."""
        cost = handle.mana_cost
        if self.caster.mana < cost:
            return False
        if handle.definition.cast_kind is not CastKind.BUFF:
            self.caster.clearcasting = False
        if cost > 0:
            self.caster.mana -= cost
            self.caster.five_second_rule_until = self.caster.time + FIVE_SECOND_RULE_SECONDS
        return True

    # --- actions ------------------------------------------------------------

    def _act(self) -> None:
        choice = self.sim.rotation.rotation_function(self.state)
        if choice is None:
            return
        handle = self.handles[choice] if isinstance(choice, SpellId) else choice
        if not handle.known:
            raise UnavailableSpellError(handle.name, handle.unavailable_reason or "is not known")
        reason = self._reject_reason(handle)
        if reason is not None:
            self.blocked[f"{handle.name}: {reason}"] += self.dt
            return
        caster = self.caster
        caster.gcd_until = self._at(self.tick + self._ticks(GCD_SECONDS))
        if handle.cooldown > 0:
            caster.cooldowns[handle.cooldown_key] = self._at(
                self.tick + self._ticks(handle.cooldown)
            )
        self.action_id += 1
        action = self.action_id
        if handle.definition.cast_kind is CastKind.CAST:
            caster.busy_until = self._at(self.tick + self._ticks(handle.cast_time))
            self._schedule(handle.cast_time, lambda: self._complete_cast(handle, action))
            return
        self._spend(handle)
        self._resolve(handle)

    def _reject_reason(self, handle: SpellHandle) -> str | None:
        if handle.on_cooldown:
            return RejectReason.COOLDOWN
        if not handle.affordable:
            return RejectReason.MANA
        if self.state.target is None:
            return RejectReason.NO_TARGET
        if (
            handle.definition.mechanics.requires_fire_totem
            and self.caster.active_fire_totem is None
        ):
            return RejectReason.NO_FIRE_TOTEM
        return None

    def _complete_cast(self, handle: SpellHandle, action: int) -> None:
        if action != self.action_id or not self.pull_active:
            return
        if not self._spend(handle):
            self.blocked[f"{handle.name}: {RejectReason.MANA}"] += handle.cast_time
            return
        if handle.spell_id is SpellId.LIGHTNING_BOLT:
            self.caster.maelstrom_stacks = 0
        self._resolve(handle)

    def _resolve(self, handle: SpellHandle) -> None:
        self.casts[_cast_label(handle)] += 1
        kind = handle.definition.cast_kind
        if kind is CastKind.MELEE:
            self._stormstrike()
        elif kind is CastKind.TOTEM:
            self._summon_totem(handle)
        elif kind is CastKind.BUFF:
            buff = handle.rank.buff
            assert buff is not None
            self.caster.attack_speed_bonus = buff.attack_speed_pct / 100.0
            self.caster.attack_speed_until = self.caster.time + buff.duration
        else:
            self._cast_damage_spell(handle)

    # --- spells -------------------------------------------------------------

    def _cast_damage_spell(self, handle: SpellHandle) -> None:
        mods = self.sim.modifiers
        self._hit_targets(handle, 1.0, handle.name)
        if handle.spell_id in OVERLOADING and self.rng.random() < mods.lightning_overload_chance:
            self._hit_targets(handle, LIGHTNING_OVERLOAD_DAMAGE, LIGHTNING_OVERLOAD)
        if mods.clearcasting_chance and self.rng.random() < mods.clearcasting_chance:
            self.caster.clearcasting = True

    def _targets(self, targeting: Targeting, count: int) -> list[Enemy]:
        alive = [e for e in self.enemies if e.alive]
        if targeting is Targeting.AOE:
            return alive
        return alive[: count if targeting is Targeting.CHAIN else 1]

    def _hit_targets(self, handle: SpellHandle, multiplier: float, source: str) -> None:
        mechanics = handle.definition.mechanics
        for jump, enemy in enumerate(self._targets(mechanics.targeting, mechanics.chain_targets)):
            self._spell_hit(handle, enemy, multiplier * mechanics.chain_falloff**jump, source)

    def _spell_hit(self, handle: SpellHandle, enemy: Enemy, multiplier: float, source: str) -> None:
        setup = self.sim.spells[handle.spell_id]
        rank, coefficients = setup.rank, setup.coefficients
        assert rank is not None and coefficients is not None
        profile = self.sim.profiles[handle.school]
        now = self.caster.time
        outcome = profile.roll(self.rng, setup.bonus_crit)
        if outcome is HitOutcome.MISS:
            return
        damage = self.rng.uniform(rank.min_damage, rank.max_damage)
        damage += profile.spell_power * coefficients.direct
        damage *= setup.damage_multiplier * multiplier
        if handle.spell_id in STORMSTRIKE_EMPOWERS and now < enemy.stormstrike_until:
            damage *= 1.0 + STORMSTRIKE_BONUS
            enemy.stormstrike_until = 0.0
        if handle.spell_id is SpellId.LAVA_BURST and SpellId.FLAME_SHOCK.value in enemy.dots:
            damage *= 1.0 + LAVA_BURST_FLAME_SHOCK_BONUS
        damage *= self.sim.resist_table.roll_multiplier(self.rng)
        if outcome is HitOutcome.CRIT:
            damage *= profile.crit_multiplier
            self._on_spell_crit()
        self._deal(enemy, damage, source)
        if enemy.alive and rank.dot is not None:
            tick = rank.dot.damage_per_tick + profile.spell_power * coefficients.dot_per_tick
            self._start_dot(
                enemy,
                DotState(
                    source=handle.name,
                    tick_damage=tick * setup.damage_multiplier,
                    ticks_left=rank.dot.ticks,
                    tick_interval=rank.dot.tick_interval,
                ),
            )

    def _on_spell_crit(self) -> None:
        if self.sim.modifiers.elemental_devastation_crit_pct:
            self.caster.devastation_until = self.caster.time + DEVASTATION_DURATION

    def _summon_totem(self, handle: SpellHandle) -> None:
        totem = handle.rank.totem
        assert totem is not None
        self.totem_id += 1
        totem_id = self.totem_id
        self.caster.fire_totem = handle.spell_id
        self.caster.fire_totem_until = self.caster.time + totem.duration
        attacks = int(totem.duration // totem.attack_interval)
        for i in range(1, attacks + 1):
            self._schedule(totem.attack_interval * i, lambda: self._totem_attack(handle, totem_id))

    def _totem_attack(self, handle: SpellHandle, totem_id: int) -> None:
        if totem_id != self.totem_id or not self.pull_active:
            return
        self._hit_targets(handle, 1.0, handle.name)

    # --- melee --------------------------------------------------------------

    def _swing_interval(self) -> float:
        caster = self.caster
        haste = 1.0
        if caster.flurry_charges > 0:
            haste *= 1.0 + self.sim.modifiers.flurry_haste
        if caster.time < caster.attack_speed_until:
            haste *= 1.0 + caster.attack_speed_bonus
        return self.sim.character.weapon.speed / haste

    def _swing(self, swing: int) -> None:
        if swing != self.swing_id or not self.pull_active:
            return
        caster = self.caster
        if caster.casting:
            delay = caster.busy_until - caster.time
            self._schedule(delay, lambda: self._swing(swing))
            return
        target = next((e for e in self.enemies if e.alive), None)
        if target is not None:
            if caster.flurry_charges > 0:
                caster.flurry_charges -= 1
            self.casts[MELEE] += 1
            outcome = self.sim.melee.roll_auto(self.rng, self._melee_bonus_crit())
            self._melee_hit(target, outcome, self.sim.attack_power, MELEE, windfury=False)
        self._schedule(self._swing_interval(), lambda: self._swing(swing))

    def _melee_bonus_crit(self) -> float:
        caster = self.caster
        if caster.time < caster.devastation_until:
            return self.sim.modifiers.elemental_devastation_crit_pct / 100.0
        return 0.0

    def _melee_hit(
        self,
        enemy: Enemy,
        outcome: HitOutcome,
        attack_power: float,
        source: str,
        *,
        windfury: bool,
    ) -> bool:
        """Apply one melee attack; True if it landed."""
        if outcome in (HitOutcome.MISS, HitOutcome.DODGE, HitOutcome.PARRY):
            return False
        melee = self.sim.melee
        damage = self.sim.weapon_damage(self.rng, attack_power) * melee.armor_multiplier
        if outcome is HitOutcome.GLANCE:
            damage *= melee.glance_multiplier(self.rng)
        elif outcome is HitOutcome.CRIT:
            damage *= MELEE_CRIT_MULTIPLIER
            if self.sim.modifiers.flurry_haste:
                self.caster.flurry_charges = FLURRY_CHARGES
        self._deal(enemy, damage, source)
        self._on_melee_landed(enemy, windfury=windfury)
        return True

    def _stormstrike(self) -> None:
        target = next((e for e in self.enemies if e.alive), None)
        if target is None:
            return
        outcome = self.sim.melee.roll_special(self.rng, self._melee_bonus_crit())
        name = SpellId.STORMSTRIKE.value
        landed = self._melee_hit(target, outcome, self.sim.attack_power, name, windfury=False)
        if landed and target.alive:
            target.stormstrike_until = self.caster.time + STORMSTRIKE_DURATION
            chance = self.sim.modifiers.improved_stormstrike_chance
            if chance and self.rng.random() < chance:
                self.caster.casting_regen_until = self.caster.time + IMPROVED_STORMSTRIKE_DURATION

    def _on_melee_landed(self, enemy: Enemy, *, windfury: bool) -> None:
        sim, caster, rng = self.sim, self.caster, self.rng
        speed = sim.character.weapon.speed
        if sim.modifiers.maelstrom_per_stack and rng.random() < (
            MAELSTROM_PROCS_PER_MINUTE * speed / SECONDS_PER_MINUTE
        ):
            caster.maelstrom_stacks = min(caster.active_maelstrom_stacks + 1, MAELSTROM_MAX_STACKS)
            caster.maelstrom_until = caster.time + MAELSTROM_DURATION
        imbue, rank = sim.rotation.weapon_imbue, sim.imbue
        if rank is None or not enemy.alive:
            return
        if imbue is WeaponImbue.FLAMETONGUE:
            base = rank.value / FLAMETONGUE_DAMAGE_DIVISOR * speed
            self._imbue_proc(enemy, School.FIRE, base, imbue.value)
        elif imbue is WeaponImbue.FROSTBRAND:
            if rng.random() < FROSTBRAND_PROCS_PER_MINUTE * speed / SECONDS_PER_MINUTE:
                self._imbue_proc(enemy, School.FROST, rank.value, imbue.value)
        elif (
            imbue is WeaponImbue.WINDFURY
            and not windfury
            and caster.time >= caster.windfury_ready_at
            and rng.random() < WINDFURY_CHANCE
        ):
            caster.windfury_ready_at = caster.time + WINDFURY_COOLDOWN
            self.casts[WINDFURY_ATTACK] += WINDFURY_EXTRA_ATTACKS
            attack_power = sim.attack_power + rank.value * sim.modifiers.windfury_multiplier
            for _ in range(WINDFURY_EXTRA_ATTACKS):
                if not enemy.alive:
                    return
                outcome = sim.melee.roll_special(rng, self._melee_bonus_crit())
                self._melee_hit(enemy, outcome, attack_power, WINDFURY_ATTACK, windfury=True)

    def _imbue_proc(self, enemy: Enemy, school: School, base: float, source: str) -> None:
        profile = self.sim.profiles[school]
        outcome = profile.roll(self.rng)
        if outcome is HitOutcome.MISS:
            return
        damage = (base + profile.spell_power * IMBUE_PROC_COEFFICIENT) * (
            self.sim.modifiers.imbue_damage_multiplier
        )
        damage *= self.sim.resist_table.roll_multiplier(self.rng)
        if outcome is HitOutcome.CRIT:
            damage *= profile.crit_multiplier
        self._deal(enemy, damage, source)

    # --- damage over time and bookkeeping ------------------------------------

    def _start_dot(self, enemy: Enemy, dot: DotState) -> None:
        enemy.dots[dot.source] = dot
        self._schedule(dot.tick_interval, lambda: self._dot_tick(enemy, dot))

    def _dot_tick(self, enemy: Enemy, dot: DotState) -> None:
        if not enemy.alive or enemy.dots.get(dot.source) is not dot:
            return
        damage = dot.tick_damage * self.sim.resist_table.roll_multiplier(self.rng)
        dot.ticks_left -= 1
        self._deal(enemy, damage, dot.source)
        if dot.ticks_left > 0 and enemy.alive:
            self._schedule(dot.tick_interval, lambda: self._dot_tick(enemy, dot))
        else:
            enemy.dots.pop(dot.source, None)

    def _deal(self, enemy: Enemy, damage: float, source: str) -> None:
        dealt = min(damage, enemy.health)
        enemy.health -= dealt
        if self.tick <= self.end_tick:
            self.damage[self.tick] += dealt
        self.damage_by_source[source] += dealt
        if not enemy.alive:
            self.kills += 1
            enemy.dots.clear()
