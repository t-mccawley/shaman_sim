"""Simulation meta parameters."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class MetaConfig:
    """Global simulation settings.

    Peak DpS ignores the first `peak_warmup_seconds`, where cumulative DpS
    divides by a near-zero time. Medians get a `confidence_level` bootstrap CI
    from `bootstrap_samples` resamples.
    """

    seed: int = 1
    iterations: int = 500
    tick_seconds: float = 0.1
    peak_warmup_seconds: float = 5.0
    confidence_level: float = 0.90
    bootstrap_samples: int = 2000
    output_dir: Path = Path("results")
    open_report: bool = True

    def __post_init__(self) -> None:
        if self.iterations < 1:
            raise ValueError("iterations must be >= 1")
        if not 0.0 < self.confidence_level < 1.0:
            raise ValueError("confidence_level must be in (0, 1)")
        if self.bootstrap_samples < 1:
            raise ValueError("bootstrap_samples must be >= 1")
        if self.tick_seconds <= 0:
            raise ValueError("tick_seconds must be positive")
        if self.peak_warmup_seconds < 0:
            raise ValueError("peak_warmup_seconds must be >= 0")
