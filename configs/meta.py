"""Simulation settings."""

from pathlib import Path

from shamansim import MetaConfig

META = MetaConfig(
    seed=42,
    iterations=300,
    tick_seconds=0.1,
    peak_warmup_seconds=5.0,
    confidence_level=0.90,
    bootstrap_samples=2000,
    output_dir=Path("results"),
    open_report=True,
)
