"""Bootstrap confidence intervals."""

import numpy as np
import pytest

from shamansim.experiment.stats import ConfidenceInterval


def _ci(values: np.ndarray, seed: int = 0) -> ConfidenceInterval:
    return ConfidenceInterval.bootstrap(
        values, np.random.default_rng(seed), samples=2000, confidence=0.90
    )


def test_interval_brackets_median() -> None:
    values = np.random.default_rng(1).normal(100.0, 10.0, size=300)
    ci = _ci(values)
    assert ci.median == pytest.approx(float(np.median(values)))
    assert ci.low < ci.median < ci.high


def test_same_seed_is_reproducible() -> None:
    values = np.random.default_rng(1).normal(100.0, 10.0, size=300)
    assert _ci(values, seed=5) == _ci(values, seed=5)


def test_more_iterations_narrow_the_interval() -> None:
    rng = np.random.default_rng(2)
    small, large = _ci(rng.normal(100, 10, 50)), _ci(rng.normal(100, 10, 5000))
    assert (large.high - large.low) < (small.high - small.low)


def test_interval_width_matches_theory() -> None:
    # Median standard error for a normal sample is ~1.2533 * sigma / sqrt(n).
    values = np.random.default_rng(3).normal(0.0, 10.0, size=2000)
    ci = _ci(values)
    expected = 2 * 1.645 * 1.2533 * 10.0 / np.sqrt(2000)
    assert ci.high - ci.low == pytest.approx(expected, rel=0.2)


def test_constant_sample_has_zero_width() -> None:
    ci = _ci(np.full(100, 7.0))
    assert (ci.low, ci.median, ci.high) == (7.0, 7.0, 7.0)
    assert str(ci) == "7.0 (7.0 - 7.0)"
