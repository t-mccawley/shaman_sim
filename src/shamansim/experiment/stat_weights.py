"""Stat weights: DpS gained per point of each stat, and equivalence points (EP).

The unmodified character and one copy per stat (raised by that stat's step)
run the same iterations with the same per-iteration seeds, so most of the
randomness cancels in the paired differences. A stat's weight is the mean
over iterations of (DpS with the stat - baseline DpS) / step; its EP is that
weight divided by the attack power weight. Weights and EPs share one bootstrap
over iterations, so EP intervals account for the correlation with attack power.

Weights use the mean, not the median: damage past an enemy's remaining health
is lost, so small stat changes often leave an iteration's DpS exactly
unchanged and the median difference collapses to zero.
"""

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Final, Protocol

import numpy as np

from shamansim.engine.results import FloatArray
from shamansim.engine.simulator import Simulation
from shamansim.experiment.candidates import Candidate, probe_problem, static_problems
from shamansim.experiment.stats import ConfidenceInterval
from shamansim.model.character import (
    Character,
    SchoolValues,
    mana_from_intellect,
    melee_crit_per_agility,
)
from shamansim.model.encounter import Encounter
from shamansim.model.meta import MetaConfig
from shamansim.model.rotation import Rotation
from shamansim.model.stat_weights import REFERENCE_STAT, Stat, StatWeightsConfig
from shamansim.model.stats import attack_power_from, sheet_stat_talents
from shamansim.spells.definitions import Spellbook
from shamansim.talents.build import TalentBuild
from shamansim.talents.effects import TalentModifiers

BASELINE_LABEL: Final = "Baseline"
BOOTSTRAP_STREAM: Final = 7

type ProgressCallback = Callable[[str, float], None]
"""Called with a variant label and its median DpS after each variant runs."""


class StatWeightsError(ValueError):
    """The stat weights config does not name a usable combination."""


@dataclass(frozen=True, slots=True)
class MeanInterval:
    """A mean with a bootstrap confidence interval."""

    mean: float
    low: float
    high: float

    @classmethod
    def from_resamples(
        cls, estimate: float, resampled: FloatArray, confidence: float
    ) -> "MeanInterval":
        """Percentile interval of an estimate's bootstrap resamples."""
        ci = ConfidenceInterval.from_resamples(estimate, resampled, confidence)
        return cls(estimate, ci.low, ci.high)

    @property
    def excludes_zero(self) -> bool:
        """True if the interval lies entirely above or below zero."""
        return self.low > 0.0 or self.high < 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class StatWeight:
    """DpS per point of one stat, and its value in attack power."""

    stat: Stat
    step: float
    dps_per_point: MeanInterval
    ep: MeanInterval


@dataclass(frozen=True, slots=True, kw_only=True)
class StatWeightsResult:
    """Stat weights for one candidate, in config order."""

    candidate: Candidate
    iterations: int
    baseline_dps: ConfidenceInterval
    weights: list[StatWeight]
    unimplemented_talents: tuple[str, ...]


class _Named(Protocol):
    @property
    def display_name(self) -> str: ...


def _by_name[T: _Named](items: Sequence[T], name: str, kind: str) -> T:
    matches = [item for item in items if item.display_name == name]
    if len(matches) == 1:
        return matches[0]
    available = ", ".join(sorted({repr(item.display_name) for item in items})) or "none"
    problem = "is ambiguous" if matches else "not found"
    raise StatWeightsError(f"{kind} {name!r} {problem}; available: {available}")


def select_candidate(
    config: StatWeightsConfig,
    characters: Sequence[Character],
    encounters: Sequence[Encounter],
    rotations: Sequence[Rotation],
) -> Candidate:
    """The configured character, encounter, rotation, and talents."""
    encounter = _by_name(encounters, config.encounter, "encounter")
    matching = [r for r in rotations if r.encounter_type is encounter.encounter_type]
    return Candidate(
        number=1,
        character=_by_name(characters, config.character, "character"),
        encounter=encounter,
        rotation=_by_name(matching, config.rotation, f"{encounter.encounter_type} rotation"),
        talents=TalentBuild.from_url(config.talents),
    )


def candidate_problems(candidate: Candidate, spellbook: Spellbook, meta: MetaConfig) -> list[str]:
    """Reasons the candidate is impossible in game (empty if valid)."""
    c = candidate
    problems = static_problems(c.character, c.rotation, c.talents, spellbook)
    if not problems:
        problem = probe_problem(c.character, c.encounter, c.rotation, c.talents, spellbook, meta)
        problems = [problem] if problem else []
    return problems


def _add_general(values: SchoolValues, amount: float) -> SchoolValues:
    return replace(values, general=values.general + amount)


def with_stat(character: Character, stat: Stat, amount: float) -> Character:
    """The character sheet after gear adds `amount` of `stat`.

    Strength, agility, and intellect from gear are scaled by the sheet's stat
    talents and also add what the sheet would show: attack power from strength
    and agility, melee crit from agility, and from intellect the mana, Mental
    Dexterity attack power, and Mental Quickness spell power.
    """
    c = character
    match stat:
        case Stat.ATTACK_POWER:
            return replace(c, attack_power=c.attack_power + amount)
        case Stat.STRENGTH:
            gained = amount * sheet_stat_talents(c).strength_multiplier
            return replace(
                c,
                strength=c.strength + gained,
                attack_power=c.attack_power + attack_power_from(gained, 0.0),
            )
        case Stat.AGILITY:
            gained = amount * sheet_stat_talents(c).agility_multiplier
            return replace(
                c,
                agility=c.agility + gained,
                attack_power=c.attack_power + attack_power_from(0.0, gained),
                melee_crit=c.melee_crit + gained * melee_crit_per_agility(c.level),
            )
        case Stat.SPELL_POWER:
            return replace(c, spell_power=_add_general(c.spell_power, amount))
        case Stat.INTELLECT:
            sheet = sheet_stat_talents(c)
            gained = amount * sheet.intellect_multiplier
            intellect = c.intellect + gained
            return replace(
                c,
                intellect=intellect,
                mana=c.mana + mana_from_intellect(intellect) - mana_from_intellect(c.intellect),
                attack_power=c.attack_power + sheet.attack_power_per_intellect * gained,
                spell_power=_add_general(c.spell_power, sheet.spell_power_per_intellect * gained),
            )
        case Stat.SPIRIT:
            return replace(c, spirit=c.spirit + amount)
        case Stat.MP5:
            return replace(c, mp5=c.mp5 + amount)
        case Stat.WEAPON_SKILL:
            return replace(c, weapon_skill_bonus=c.weapon_skill_bonus + round(amount))
        case Stat.MELEE_CRIT:
            return replace(c, melee_crit=c.melee_crit + amount)
        case Stat.MELEE_HIT:
            return replace(c, melee_hit=c.melee_hit + amount)
        case Stat.SPELL_CRIT:
            return replace(c, spell_crit=_add_general(c.spell_crit, amount))
        case Stat.SPELL_HIT:
            return replace(c, spell_hit=_add_general(c.spell_hit, amount))


def _total_dps(
    candidate: Candidate,
    character: Character,
    spellbook: Spellbook,
    meta: MetaConfig,
    iterations: int,
) -> FloatArray:
    """Total DpS per iteration; iteration i always uses the same seed."""
    sim = Simulation(
        character,
        candidate.encounter,
        candidate.talents,
        candidate.rotation,
        spellbook,
        tick_seconds=meta.tick_seconds,
        peak_warmup_seconds=meta.peak_warmup_seconds,
    )
    return np.array(
        [sim.run(random.Random(f"{meta.seed}:{i}")).total_dps for i in range(iterations)],
        dtype=np.float64,
    )


def weigh(
    baseline: FloatArray,
    totals: dict[Stat, FloatArray],
    steps: dict[Stat, float],
    meta: MetaConfig,
) -> tuple[ConfidenceInterval, list[StatWeight]]:
    """Baseline DpS and per-stat weights from paired per-iteration DpS."""
    if REFERENCE_STAT not in totals:
        raise ValueError(f"EP needs {REFERENCE_STAT.name} results")
    rng = np.random.default_rng([meta.seed, BOOTSTRAP_STREAM])
    n = baseline.size
    resample = rng.integers(0, n, size=(meta.bootstrap_samples, n))
    confidence = meta.confidence_level

    def mean(values: FloatArray) -> tuple[float, FloatArray]:
        return float(np.mean(values)), np.mean(values[resample], axis=1)

    per_point = {stat: mean((dps - baseline) / steps[stat]) for stat, dps in totals.items()}
    reference, reference_resampled = per_point[REFERENCE_STAT]
    weights = []
    for stat, (estimate, resampled) in per_point.items():
        with np.errstate(divide="ignore", invalid="ignore"):
            ep_resampled = resampled / reference_resampled
        ep = estimate / reference if reference else math.nan
        weights.append(
            StatWeight(
                stat=stat,
                step=steps[stat],
                dps_per_point=MeanInterval.from_resamples(estimate, resampled, confidence),
                ep=MeanInterval.from_resamples(ep, ep_resampled, confidence),
            )
        )
    base = ConfidenceInterval.from_resamples(
        float(np.median(baseline)), np.median(baseline[resample], axis=1), confidence
    )
    return base, weights


def ranked_by_ep(weights: list[StatWeight]) -> list[StatWeight]:
    """Highest EP first; undefined EPs last."""
    return sorted(
        weights, key=lambda w: -math.inf if math.isnan(w.ep.mean) else w.ep.mean, reverse=True
    )


def variant_label(stat: Stat, step: float) -> str:
    """E.g. 'Attack power +50' or 'Melee crit +2%'."""
    suffix = "%" if stat.info.percent else ""
    return f"{stat.info.name} +{step:g}{suffix}"


def run_stat_weights(
    candidate: Candidate,
    steps: dict[Stat, float],
    spellbook: Spellbook,
    meta: MetaConfig,
    iterations: int,
    on_done: ProgressCallback | None = None,
) -> StatWeightsResult:
    """Simulate the baseline and one variant per stat, then weigh them."""

    def run(label: str, character: Character) -> FloatArray:
        dps = _total_dps(candidate, character, spellbook, meta, iterations)
        if on_done is not None:
            on_done(label, float(np.median(dps)))
        return dps

    baseline = run(BASELINE_LABEL, candidate.character)
    totals = {
        stat: run(variant_label(stat, step), with_stat(candidate.character, stat, step))
        for stat, step in steps.items()
    }
    baseline_dps, weights = weigh(baseline, totals, steps, meta)
    return StatWeightsResult(
        candidate=candidate,
        iterations=iterations,
        baseline_dps=baseline_dps,
        weights=weights,
        unimplemented_talents=TalentModifiers.from_build(candidate.talents).unimplemented,
    )
