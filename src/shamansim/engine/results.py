"""Outputs of a single simulation iteration."""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

type FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True, slots=True, kw_only=True)
class IterationResult:
    """One Monte Carlo iteration."""

    total_dps: float
    peak_dps: float
    dps_series: FloatArray
    elapsed: float
    damage_by_source: dict[str, float]
    casts: dict[str, int]
    blocked_seconds: dict[str, float]
    enemies_killed: int
    drinking_time: float


def dps_series(damage_per_tick: FloatArray, tick_seconds: float, end_tick: int) -> FloatArray:
    """Cumulative DpS at ticks 1..N; NaN after `end_tick`."""
    cumulative = np.cumsum(damage_per_tick)
    times = np.arange(1, damage_per_tick.size, dtype=np.float64) * tick_seconds
    series = cumulative[1:] / times
    series[end_tick:] = np.nan
    return series


def peak_dps(series: FloatArray, warmup_ticks: int) -> float:
    """Max DpS after the warmup window (whole series if the fight is shorter)."""
    tail = series[warmup_ticks:]
    window = tail if tail.size and not np.all(np.isnan(tail)) else series
    return float(np.nanmax(window))
