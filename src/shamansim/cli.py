"""`shamansim` command line entry point."""

import argparse
import sys
import webbrowser
from pathlib import Path

from shamansim.config_loader import Configs, load_configs, load_spellbook, load_stat_weights
from shamansim.experiment.candidates import Candidate, InvalidCandidate, plan_candidates
from shamansim.experiment.runner import run_all
from shamansim.experiment.stat_weights import (
    StatWeightsError,
    candidate_problems,
    ranked_by_ep,
    run_stat_weights,
    select_candidate,
)
from shamansim.experiment.stats import CandidateSummary
from shamansim.report.html import write_report
from shamansim.report.stat_weights_html import STAT_WEIGHTS_FILE, write_stat_weights
from shamansim.spells.export import write_spellbook_csv
from shamansim.talents.wowhead import refresh_snapshot

RUN_COMMAND = "run"
SPELLBOOK_COMMAND = "spellbook"
STAT_WEIGHTS_COMMAND = "stat-weights"
STDOUT_PATH = "-"
DEFAULT_SPELLBOOK_CSV = Path("results") / "spellbook.csv"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="shamansim", description="WoW Forever shaman DpS simulator."
    )
    parser.add_argument("--configs", type=Path, default=Path("configs"), help="configs directory")
    parser.add_argument("--no-open", action="store_true", help="do not open the report")
    parser.add_argument(
        "--refresh-talents", action="store_true", help="re-download Wowhead talent data first"
    )
    commands = parser.add_subparsers(dest="command")
    commands.add_parser(RUN_COMMAND, help="simulate all candidates (default)")
    spellbook = commands.add_parser(
        SPELLBOOK_COMMAND, help="export configured spell ranks and calculated coefficients"
    )
    spellbook.add_argument(
        "--out",
        default=str(DEFAULT_SPELLBOOK_CSV),
        help=f"CSV path, or '{STDOUT_PATH}' for stdout (default: {DEFAULT_SPELLBOOK_CSV})",
    )
    commands.add_parser(
        STAT_WEIGHTS_COMMAND,
        help=f"DpS per point of each stat for configs/stat_weights.py; writes {STAT_WEIGHTS_FILE}",
    )
    return parser.parse_args(argv)


def _export_spellbook(configs_dir: Path, out: str) -> int:
    spellbook = load_spellbook(configs_dir)
    if out == STDOUT_PATH:
        write_spellbook_csv(spellbook, None)
        return 0
    path = Path(out)
    write_spellbook_csv(spellbook, path)
    print(f"Spellbook: {path.resolve()}")
    return 0


def _print_invalid(invalid: list[InvalidCandidate]) -> None:
    for c in invalid:
        print(
            f"  invalid: {c.rotation.display_name} | {c.talents.display_name} | "
            f"{c.encounter.display_name} | {c.character.display_name}"
        )
        for reason in c.reasons:
            print(f"      - {reason}")


def _print_unpaired(configs: Configs) -> None:
    types = {e.encounter_type for e in configs.encounters}
    for rotation in configs.rotations:
        if rotation.encounter_type not in types:
            kind = rotation.encounter_type
            print(f"  skipped rotation {rotation.display_name}: no {kind} encounter")


def _progress(candidate: Candidate, summary: CandidateSummary) -> None:
    d = summary.total_dps
    print(
        f"  {candidate.label:>4} {d!s:>22} DpS  "
        f"{candidate.rotation.display_name} | {candidate.talents.display_name} | "
        f"{candidate.encounter.display_name}"
    )


def _open(path: Path, configs: Configs, no_open: bool) -> None:
    if configs.meta.open_report and not no_open:
        webbrowser.open(path.resolve().as_uri())


def _stat_weights(configs_dir: Path, no_open: bool) -> int:
    configs = load_configs(configs_dir)
    config = load_stat_weights(configs_dir)
    try:
        candidate = select_candidate(
            config, configs.characters, configs.encounters, configs.rotations
        )
    except StatWeightsError as error:
        print(f"stat_weights.py: {error}", file=sys.stderr)
        return 1
    problems = candidate_problems(candidate, configs.spellbook, configs.meta)
    if problems:
        print("stat_weights.py: this combination is invalid:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    iterations = config.iterations or configs.meta.iterations
    print(
        f"Stat weights: {candidate.rotation.display_name} | {candidate.talents.display_name} | "
        f"{candidate.encounter.display_name} | {candidate.character.display_name}, "
        f"{len(config.steps)} stats, {iterations} iterations each"
    )
    result = run_stat_weights(
        candidate,
        config.steps,
        configs.spellbook,
        configs.meta,
        iterations,
        on_done=lambda label, dps: print(f"  {label:<22} {dps:8.1f} DpS"),
    )
    for w in ranked_by_ep(result.weights):
        print(
            f"  {w.stat.info.name:<14} EP {w.ep.mean:6.2f}   "
            f"{w.dps_per_point.mean:.4f} DpS per {w.stat.info.unit}"
        )
    path = write_stat_weights(result, configs.meta)
    print(f"Report: {path.resolve()}")
    _open(path, configs, no_open)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run a ShamanSim command (default: simulate and write the HTML report)."""
    args = _parse_args(argv)
    if args.command == SPELLBOOK_COMMAND:
        return _export_spellbook(args.configs, args.out)
    if args.refresh_talents:
        print(f"Talent data refreshed: {refresh_snapshot()}")
    if args.command == STAT_WEIGHTS_COMMAND:
        return _stat_weights(args.configs, args.no_open)
    configs = load_configs(args.configs)
    plan = plan_candidates(
        configs.characters,
        configs.encounters,
        configs.rotations,
        configs.talents,
        configs.spellbook,
        configs.meta,
    )
    print(
        f"{len(plan.valid)} valid candidates ({len(plan.invalid)} invalid), "
        f"{configs.meta.iterations} iterations each"
    )
    _print_unpaired(configs)
    _print_invalid(plan.invalid)
    if not plan.valid:
        print("Nothing to simulate: every combination is invalid.", file=sys.stderr)
        return 1
    results = run_all(plan.valid, configs.spellbook, configs.meta, on_done=_progress)
    _print_invalid(results.invalid)
    invalid = plan.invalid + results.invalid
    path = write_report(results.summaries, invalid, configs.meta)
    print(f"Report: {path.resolve()}")
    _open(path, configs, args.no_open)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
