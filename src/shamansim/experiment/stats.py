"""Aggregation of iteration results."""

import warnings
from collections import Counter
from dataclasses import dataclass

import numpy as np

from shamansim.engine.results import FloatArray, IterationResult
from shamansim.experiment.candidates import Candidate
from shamansim.model.meta import MetaConfig


@dataclass(frozen=True, slots=True)
class ConfidenceInterval:
    """Median with a bootstrap confidence interval on the median."""

    median: float
    low: float
    high: float

    @classmethod
    def bootstrap(
        cls,
        values: FloatArray,
        rng: np.random.Generator,
        *,
        samples: int,
        confidence: float,
    ) -> "ConfidenceInterval":
        """Percentile bootstrap: resample with replacement, take each resample's median."""
        resamples = values[rng.integers(0, values.size, size=(samples, values.size))]
        medians = np.median(resamples, axis=1)
        tail = (1.0 - confidence) / 2.0
        low, high = np.quantile(medians, [tail, 1.0 - tail])
        return cls(float(np.median(values)), float(low), float(high))

    def __str__(self) -> str:
        return f"{self.median:.1f} ({self.low:.1f} - {self.high:.1f})"


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateSummary:
    """Aggregated results for one candidate."""

    candidate: Candidate
    iterations: int
    total_dps: ConfidenceInterval
    peak_dps: ConfidenceInterval
    times: FloatArray
    median_dps_series: FloatArray
    damage_share: dict[str, float]
    casts_per_iteration: dict[str, float]
    blocked_seconds_per_iteration: dict[str, float]
    mean_kills: float
    mean_drinking_time: float
    unimplemented_talents: tuple[str, ...]


def summarize(
    candidate: Candidate,
    results: list[IterationResult],
    meta: MetaConfig,
    unimplemented_talents: tuple[str, ...],
) -> CandidateSummary:
    """Reduce iterations to median DpS with bootstrap CIs and a median time series."""
    n = len(results)
    rng = np.random.default_rng([meta.seed, candidate.number])

    def interval(values: list[float]) -> ConfidenceInterval:
        return ConfidenceInterval.bootstrap(
            np.array(values),
            rng,
            samples=meta.bootstrap_samples,
            confidence=meta.confidence_level,
        )

    series = np.vstack([r.dps_series for r in results])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        median_series = np.nanmedian(series, axis=0)
    damage: Counter[str] = Counter()
    casts: Counter[str] = Counter()
    blocked: Counter[str] = Counter()
    for r in results:
        damage.update(r.damage_by_source)
        casts.update(r.casts)
        blocked.update(r.blocked_seconds)
    total_damage = sum(damage.values()) or 1.0
    return CandidateSummary(
        candidate=candidate,
        iterations=n,
        total_dps=interval([r.total_dps for r in results]),
        peak_dps=interval([r.peak_dps for r in results]),
        times=np.arange(1, series.shape[1] + 1, dtype=np.float64) * meta.tick_seconds,
        median_dps_series=median_series,
        damage_share={k: v / total_damage for k, v in damage.most_common()},
        casts_per_iteration={k: v / n for k, v in casts.most_common()},
        blocked_seconds_per_iteration={k: v / n for k, v in blocked.most_common()},
        mean_kills=float(np.mean([r.enemies_killed for r in results])),
        mean_drinking_time=float(np.mean([r.drinking_time for r in results])),
        unimplemented_talents=unimplemented_talents,
    )
