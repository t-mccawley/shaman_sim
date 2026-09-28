"""Monte Carlo execution of candidates."""

import random
from collections.abc import Callable
from dataclasses import dataclass

from shamansim.engine.simulator import Simulation
from shamansim.engine.state import UnavailableSpellError
from shamansim.experiment.candidates import Candidate, InvalidCandidate
from shamansim.experiment.stats import CandidateSummary, summarize
from shamansim.model.meta import MetaConfig
from shamansim.spells.definitions import Spellbook

type ProgressCallback = Callable[[Candidate, CandidateSummary], None]


@dataclass(frozen=True, slots=True)
class RunResults:
    """Summaries of completed candidates, plus any found invalid mid-run."""

    summaries: list[CandidateSummary]
    invalid: list[InvalidCandidate]


def run_candidate(candidate: Candidate, spellbook: Spellbook, meta: MetaConfig) -> CandidateSummary:
    """Simulate one candidate for `meta.iterations` iterations."""
    sim = Simulation(
        candidate.character,
        candidate.encounter,
        candidate.talents,
        candidate.rotation,
        spellbook,
        tick_seconds=meta.tick_seconds,
        peak_warmup_seconds=meta.peak_warmup_seconds,
    )
    rng = random.Random(f"{meta.seed}:{candidate.number}")
    results = [sim.run(rng) for _ in range(meta.iterations)]
    return summarize(candidate, results, meta, sim.modifiers.unimplemented)


def run_all(
    candidates: list[Candidate],
    spellbook: Spellbook,
    meta: MetaConfig,
    on_done: ProgressCallback | None = None,
) -> RunResults:
    """Simulate every candidate in order."""
    summaries: list[CandidateSummary] = []
    invalid: list[InvalidCandidate] = []
    for candidate in candidates:
        try:
            summary = run_candidate(candidate, spellbook, meta)
        except UnavailableSpellError as error:
            invalid.append(InvalidCandidate.of(candidate, str(error)))
            continue
        summaries.append(summary)
        if on_done is not None:
            on_done(candidate, summary)
    return RunResults(summaries, invalid)
