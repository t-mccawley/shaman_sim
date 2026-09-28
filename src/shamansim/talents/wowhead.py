"""Wowhead Forever talent data and calculator URL decoding.

URL format (from Wowhead's TalentCalcClassic.js):
    .../talent-calc/shaman/<version><tree0>-<tree1>-<tree2>[_<suffix>...][/<pick order>]
Each tree string holds one rank digit per talent, ordered by (row, col); trailing
zeros and empty trailing trees may be omitted. Suffix `t<n>` is the Talented perk
rank, which lowers the first talent level by n. Wowhead bumps <version> when its
data changes and ignores links with an old version. Builds must follow the
calculator rules: 5 points in a tree per row above a talent, and prerequisites.
"""

import json
import re
import urllib.request
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Final

from shamansim.core.enums import TalentTree

CALCULATOR_URL: Final = "https://www.wowhead.com/forever/talent-calc/shaman"
SNAPSHOT_FILE: Final = "forever_shaman_talents.json"
TALENTED_SUFFIX: Final = "t"
POINTS_PER_ROW: Final = 5
FIRST_TALENT_LEVEL: Final = 10

# Wowhead tree ids for the shaman, in calculator order.
TREE_IDS: Final[dict[TalentTree, str]] = {
    TalentTree.ELEMENTAL: "261",
    TalentTree.ENHANCEMENT: "263",
    TalentTree.RESTORATION: "262",
}

_URL_PATTERN: Final = re.compile(r"talent-calc/shaman/([^/?#]+)")
_DATA_URL_PATTERN: Final = re.compile(
    r"https://nether\.wowhead\.com/forever/data/talents-classic\?[^\"'\s]+"
)
_HEADERS: Final = {"User-Agent": "Mozilla/5.0"}


@dataclass(frozen=True, slots=True)
class TalentInfo:
    """One talent in a tree."""

    talent_id: int
    tree: TalentTree
    name: str
    row: int
    col: int
    max_rank: int
    description: str
    requires: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class TalentData:
    """Snapshot of the shaman talent trees."""

    hash_version: str
    trees: dict[TalentTree, tuple[TalentInfo, ...]]


@dataclass(frozen=True, slots=True)
class DecodedBuild:
    """Ranks parsed from a calculator URL."""

    ranks: dict[str, int]
    points: dict[TalentTree, int]
    talented_rank: int


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        text: str = response.read().decode("utf-8")
    return text


def refresh_snapshot(target: Path | None = None) -> Path:
    """Download the talent data the live calculator uses and write the snapshot."""
    match = _DATA_URL_PATTERN.search(_fetch(CALCULATOR_URL))
    if match is None:
        raise RuntimeError(f"talent data URL not found on {CALCULATOR_URL}")
    text = _fetch(match.group(0).replace("&amp;", "&"))
    payload = json.JSONDecoder().raw_decode(text[text.index(",") + 1 :])[0]
    snapshot = {
        "hash_version": payload["hashVersion"],
        "trees": {
            tree.value: [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "row": t["row"],
                    "col": t["col"],
                    "max_rank": len(t["ranks"]),
                    "description": t["descriptions"][str(len(t["ranks"]))],
                    "requires": [[r["id"], r["qty"]] for r in t["requires"]],
                }
                for t in payload["talents"][tree_id].values()
            ]
            for tree, tree_id in TREE_IDS.items()
        },
    }
    path = target or Path(str(resources.files("shamansim.data").joinpath(SNAPSHOT_FILE)))
    path.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
    load_talent_data.cache_clear()
    return path


@cache
def load_talent_data() -> TalentData:
    """Talent snapshot with each tree ordered by (row, col)."""
    raw = json.loads(
        resources.files("shamansim.data").joinpath(SNAPSHOT_FILE).read_text(encoding="utf-8")
    )
    trees: dict[TalentTree, tuple[TalentInfo, ...]] = {}
    for tree in TalentTree:
        infos = [
            TalentInfo(
                talent_id=t["id"],
                tree=tree,
                name=t["name"],
                row=t["row"],
                col=t["col"],
                max_rank=t["max_rank"],
                description=t["description"],
                requires=tuple((r[0], r[1]) for r in t["requires"]),
            )
            for t in raw["trees"][tree.value]
        ]
        trees[tree] = tuple(sorted(infos, key=lambda t: (t.row, t.col)))
    return TalentData(hash_version=raw["hash_version"], trees=trees)


def decode_url(url: str) -> DecodedBuild:
    """Parse a Wowhead Forever shaman talent calculator URL."""
    match = _URL_PATTERN.search(url)
    if match is None:
        raise ValueError(f"not a Wowhead shaman talent calculator URL: {url}")
    data = load_talent_data()
    code = match.group(1)
    if not code.startswith(data.hash_version):
        raise ValueError(
            f"talent link {url} is not in Wowhead's current format "
            f"({data.hash_version}); re-open the build in the calculator and copy the new "
            "link, or run `shamansim --refresh-talents` if Wowhead has updated"
        )
    points_code, *suffixes = code[len(data.hash_version) :].split("_")
    talented_rank = 0
    for suffix in suffixes:
        if suffix.startswith(TALENTED_SUFFIX) and suffix[1:].isdigit():
            talented_rank = int(suffix[1:])

    tree_codes = points_code.split("-")
    ranks: dict[str, int] = {}
    points: dict[TalentTree, int] = {}
    for index, tree in enumerate(TalentTree):
        digits = tree_codes[index] if index < len(tree_codes) else ""
        talents = data.trees[tree]
        if len(digits) > len(talents):
            raise ValueError(f"{tree} has {len(talents)} talents, URL gives {len(digits)}")
        spent = 0
        for talent, digit in zip(talents, digits, strict=False):
            rank = int(digit)
            if rank > talent.max_rank:
                raise ValueError(f"{talent.name} rank {rank} exceeds max {talent.max_rank}")
            if rank:
                ranks[talent.name] = rank
                spent += rank
        points[tree] = spent
    _check_rules(data, ranks)
    return DecodedBuild(ranks=ranks, points=points, talented_rank=talented_rank)


def _check_rules(data: TalentData, ranks: dict[str, int]) -> None:
    """Reject builds the calculator would not allow."""
    by_id = {t.talent_id: t for talents in data.trees.values() for t in talents}
    for tree, talents in data.trees.items():
        for talent in talents:
            if not ranks.get(talent.name):
                continue
            above = sum(ranks.get(t.name, 0) for t in talents if t.row < talent.row)
            needed = talent.row * POINTS_PER_ROW
            if above < needed:
                raise ValueError(
                    f"{talent.name} needs {needed} points in {tree.value} rows above it, "
                    f"build has {above}"
                )
            for required_id, qty in talent.requires:
                prerequisite = by_id[required_id]
                if ranks.get(prerequisite.name, 0) < qty:
                    raise ValueError(f"{talent.name} requires {qty} points in {prerequisite.name}")
