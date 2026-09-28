"""Spellbook audit export."""

import csv
import dataclasses
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from shamansim.spells.coefficients import IMBUE_PROC_COEFFICIENT, calculate
from shamansim.spells.definitions import Spellbook
from shamansim.spells.mechanics import IMBUE_SCHOOLS

IMBUE_KIND: Final = "imbue"


@dataclass(frozen=True, slots=True, kw_only=True)
class SpellbookRow:
    """One CSV row: configured values followed by calculated values."""

    spell: str
    rank: int
    level: int
    school: str
    cast_kind: str
    targeting: str
    min_damage: float = 0.0
    max_damage: float = 0.0
    average_damage: float = 0.0
    imbue_value: float = 0.0
    mana_cost: float = 0.0
    base_mana_pct: float = 0.0
    cast_time: float = 0.0
    cooldown: float = 0.0
    dot_damage: float = 0.0
    dot_duration: float = 0.0
    dot_ticks: int = 0
    totem_duration: float = 0.0
    totem_attack_interval: float = 0.0
    buff_duration: float = 0.0
    buff_attack_speed_pct: float = 0.0
    wowhead_id: int | None = None
    confirmed_in_game_date: str | None = None
    direct_base: float = 0.0
    direct_scale: float = 0.0
    direct_coefficient: float = 0.0
    dot_base: float = 0.0
    dot_scale: float = 0.0
    dot_coefficient_per_tick: float = 0.0
    scale_note: str = ""


def spellbook_rows(spellbook: Spellbook) -> list[SpellbookRow]:
    """Every configured spell and imbue rank with calculated coefficients."""
    rows: list[SpellbookRow] = []
    for definition in spellbook.spells.values():
        m = definition.mechanics
        for rank in sorted(definition.ranks, key=lambda r: r.rank):
            c = calculate(m, rank)
            rows.append(
                SpellbookRow(
                    spell=definition.name,
                    rank=rank.rank,
                    level=rank.level,
                    school=m.school.value,
                    cast_kind=m.cast_kind.value,
                    targeting=m.targeting.value,
                    min_damage=rank.min_damage,
                    max_damage=rank.max_damage,
                    average_damage=rank.average_damage,
                    mana_cost=rank.mana_cost,
                    base_mana_pct=rank.base_mana_pct,
                    cast_time=rank.cast_time,
                    cooldown=rank.cooldown,
                    dot_damage=rank.dot.damage if rank.dot else 0.0,
                    dot_duration=rank.dot.duration if rank.dot else 0.0,
                    dot_ticks=rank.dot.ticks if rank.dot else 0,
                    totem_duration=rank.totem.duration if rank.totem else 0.0,
                    totem_attack_interval=rank.totem.attack_interval if rank.totem else 0.0,
                    buff_duration=rank.buff.duration if rank.buff else 0.0,
                    buff_attack_speed_pct=rank.buff.attack_speed_pct if rank.buff else 0.0,
                    wowhead_id=rank.wowhead_id,
                    confirmed_in_game_date=rank.confirmed_in_game_date,
                    direct_base=round(c.direct_base, 4),
                    direct_scale=round(m.direct_scale, 4),
                    direct_coefficient=round(c.direct, 4),
                    dot_base=round(c.dot_base, 4),
                    dot_scale=round(m.dot_scale, 4),
                    dot_coefficient_per_tick=round(c.dot_per_tick, 4),
                    scale_note=m.scale_note,
                )
            )
    for imbue, ranks in spellbook.imbues.items():
        school = IMBUE_SCHOOLS.get(imbue)
        for imbue_rank in sorted(ranks, key=lambda r: r.rank):
            rows.append(
                SpellbookRow(
                    spell=imbue.value,
                    rank=imbue_rank.rank,
                    level=imbue_rank.level,
                    school=school.value if school else "",
                    cast_kind=IMBUE_KIND,
                    targeting="",
                    imbue_value=imbue_rank.value,
                    mana_cost=imbue_rank.mana_cost,
                    wowhead_id=imbue_rank.wowhead_id,
                    confirmed_in_game_date=imbue_rank.confirmed_in_game_date,
                    direct_coefficient=IMBUE_PROC_COEFFICIENT if school else 0.0,
                    scale_note="proc spell power coefficient (wowsims)" if school else "",
                )
            )
    return rows


def write_spellbook_csv(spellbook: Spellbook, path: Path | None) -> None:
    """Write the audit CSV to `path`, or stdout when None."""
    fields = [f.name for f in dataclasses.fields(SpellbookRow)]
    rows = [dataclasses.asdict(r) for r in spellbook_rows(spellbook)]
    if path is None:
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
