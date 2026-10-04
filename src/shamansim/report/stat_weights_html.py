"""Self-contained stat weights report."""

import math
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Final

import plotly.graph_objects as go

from shamansim.experiment.stat_weights import (
    MeanInterval,
    StatWeight,
    StatWeightsResult,
    ranked_by_ep,
)
from shamansim.model.meta import MetaConfig
from shamansim.model.stat_weights import REFERENCE_STAT
from shamansim.report.html import (
    BAR_COLOR,
    BASE_CSS,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    esc,
    style_figure,
)

STAT_WEIGHTS_FILE: Final = "stat_weights_results.html"
MAX_DECIMALS: Final = 4
SIGNIFICANT_DIGITS: Final = 3


def _sig(value: float) -> str:
    """About three significant digits, without scientific notation."""
    if math.isnan(value):
        return "n/a"
    if value == 0:
        return "0"
    magnitude = math.floor(math.log10(abs(value)))
    decimals = min(max(SIGNIFICANT_DIGITS - 1 - magnitude, 0), MAX_DECIMALS)
    return f"{value:.{decimals}f}"


def _ep(value: float) -> str:
    return "n/a" if math.isnan(value) else f"{value:.2f}"


def _range(ci: MeanInterval, fmt: Callable[[float], str] = _sig) -> str:
    return f"{fmt(ci.low)} - {fmt(ci.high)}"


def _unit(w: StatWeight) -> str:
    return w.stat.info.unit


def _step(w: StatWeight) -> str:
    return f"+{w.step:g}{'%' if w.stat.info.percent else ''}"


def _hover(w: StatWeight) -> str:
    d = w.dps_per_point
    return "<br>".join(
        [
            f"<b>{esc(w.stat.info.name)}</b>",
            f"DpS per {_unit(w)}: {_sig(d.mean)} ({_range(d)})",
            f"EP: {_ep(w.ep.mean)} ({_range(w.ep, _ep)})",
            f"Simulated step: {_step(w)}",
        ]
    )


def _weights_chart(
    weights: list[StatWeight], title: str, unit: str, confidence: float
) -> go.Figure:
    """Median DpS per point, CI whiskers, value labels past the whisker; best on top."""
    ranked = sorted(weights, key=lambda w: w.dps_per_point.mean)
    names = [w.stat.info.name for w in ranked]
    stats = [w.dps_per_point for w in ranked]
    hover = [_hover(w) for w in ranked]
    fig = go.Figure(
        [
            go.Bar(
                x=[ci.mean for ci in stats],
                y=names,
                orientation="h",
                marker={"color": BAR_COLOR, "cornerradius": 4},
                error_x={
                    "type": "data",
                    "symmetric": False,
                    "color": TEXT_SECONDARY,
                    "thickness": 1.5,
                    "array": [ci.high - ci.mean for ci in stats],
                    "arrayminus": [ci.mean - ci.low for ci in stats],
                },
                customdata=hover,
                hovertemplate="%{customdata}<extra></extra>",
            ),
            go.Scatter(
                x=[max(ci.high, 0.0) for ci in stats],
                y=names,
                mode="text",
                text=[f"  {_sig(ci.mean)}" for ci in stats],
                textposition="middle right",
                textfont={"color": TEXT_PRIMARY},
                customdata=hover,
                hovertemplate="%{customdata}<extra></extra>",
            ),
        ]
    )
    style_figure(
        fig,
        f"{title} (mean, whiskers {confidence:.0%} CI)",
        height=max(200, 56 * len(weights) + 110),
    )
    low = min(0.0, *(ci.low for ci in stats))
    high = max(0.0, *(ci.high for ci in stats))
    span = (high - low) or 1.0
    fig.update_layout(showlegend=False, bargap=0.35)
    fig.update_xaxes(
        title=f"DpS per {unit}",
        range=[low - 0.02 * span if low < 0 else 0.0, high + 0.22 * span],
        zeroline=True,
        zerolinecolor=TEXT_SECONDARY,
    )
    return fig


def _table(result: StatWeightsResult, confidence: float) -> str:
    """Stats by EP, best first."""
    ci = f"{confidence:.0%} CI"
    rows = []
    for w in ranked_by_ep(result.weights):
        d = w.dps_per_point
        notes = []
        if w.stat is REFERENCE_STAT:
            notes.append("Reference: EP = 1 by definition.")
        if not w.dps_per_point.excludes_zero:
            notes.append("CI includes 0: no measurable effect at this step.")
        rows.append(
            "<tr>"
            f"<td><b>{esc(w.stat.info.name)}</b></td>"
            f"<td class='num'>{esc(_unit(w))}</td>"
            f"<td class='num'>{esc(_step(w))}</td>"
            f"<td class='num'>{_sig(d.mean)}</td>"
            f"<td class='num muted'>{_range(d)}</td>"
            f"<td class='num'><b>{_ep(w.ep.mean)}</b></td>"
            f"<td class='num muted'>{_range(w.ep, _ep)}</td>"
            f"<td class='muted'>{esc(' '.join(notes))}</td>"
            "</tr>"
        )
    return f"""
<h2>Equivalence points (1 attack power = 1.00)</h2>
<p class="muted note">EP = a stat's DpS per point divided by attack power's DpS per point:
how much attack power one point of the stat is worth. Percent stats are per 1%.</p>
<div class="scroll"><table class="plain"><thead><tr>
<th>Stat</th><th>Per</th><th>Simulated step</th><th>DpS per point</th><th>DpS {ci}</th>
<th>EP</th><th>EP {ci}</th><th>Notes</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>"""


def _setup_html(result: StatWeightsResult) -> str:
    c = result.candidate
    rotation = c.rotation
    items = [
        ("Character", f"{esc(c.character.display_name)} (L{c.character.level})"),
        ("Encounter", f"{esc(c.encounter.display_name)}: {esc(c.encounter.description)}"),
        (
            "Rotation",
            f"{esc(rotation.display_name)}: {esc(rotation.description)} "
            f"Imbue: {esc(rotation.weapon_imbue.value)}.",
        ),
        ("Talents", f"<a href='{esc(c.talents.url)}'>{esc(c.talents.display_name)}</a>"),
    ]
    if result.unimplemented_talents:
        items.append(("Unmodeled talents", esc(", ".join(result.unimplemented_talents))))
    rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in items)
    base = result.baseline_dps
    return f"""
<div class="hero"><span class="hero-value">{base.median:.1f}</span>
<span class="muted">median baseline total DpS ({base.low:.1f} - {base.high:.1f})</span></div>
<table class="plain setup"><tbody>{rows}</tbody></table>"""


_CSS: Final = f"""{BASE_CSS}
.hero {{ margin:8px 8px 12px; display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }}
.hero-value {{ font-size:32px; font-weight:600; font-variant-numeric:tabular-nums; }}
table.setup th {{ width:1%; padding-right:16px; }}
table.setup td a {{ white-space:normal; }}
"""


def render_stat_weights(result: StatWeightsResult, meta: MetaConfig) -> str:
    """Build the stat weights report HTML."""
    confidence = meta.confidence_level
    groups = [
        ("DpS per point", "point", [w for w in result.weights if not w.stat.info.percent]),
        ("DpS per 1%", "1%", [w for w in result.weights if w.stat.info.percent]),
    ]
    figs = [
        _weights_chart(weights, title, unit, confidence)
        for title, unit, weights in groups
        if weights
    ]
    divs = "".join(
        "<div class='card'>"
        + fig.to_html(
            full_html=False,
            include_plotlyjs="cdn" if i == 0 else False,
            config={"displaylogo": False, "responsive": True},
        )
        + "</div>"
        for i, fig in enumerate(figs)
    )
    subtitle = " · ".join(
        [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            f"{result.iterations} iterations per stat",
            f"seed {meta.seed}",
            f"tick {meta.tick_seconds}s",
            f"CI = {confidence:.0%} bootstrap CI ({meta.bootstrap_samples} resamples) of the "
            "median baseline DpS and of the mean DpS per point",
        ]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ShamanSim Stat Weights</title><style>{_CSS}</style></head>
<body><main>
<h1>ShamanSim stat weights</h1>
<div class="muted">{subtitle}</div>
<div class="card">{_setup_html(result)}</div>
{divs}
<div class="card">{_table(result, confidence)}</div>
<p class="muted note">Method: the unmodified character and one copy per stat, raised by the
simulated step, run the same {result.iterations} iterations with the same random seeds.
DpS per point is the mean of the per-iteration DpS differences divided by the step
(the mean, because damage past an enemy's remaining health is lost, which makes many small
differences exactly zero and the median misleading).
Values are averages over the step, so a stat near a cap (such as hit) can be worth less
than shown, and against low-health enemies, where extra damage pays off in jumps as hits
start killing in fewer swings, they can change with the step size.
Strength, agility, and intellect are gear points: the sheet's talents scale them, strength
adds 2 attack power, agility adds melee crit by level, and intellect adds mana, Mental
Dexterity attack power, and Mental Quickness spell power.</p>
</main></body></html>"""


def write_stat_weights(result: StatWeightsResult, meta: MetaConfig) -> Path:
    """Write the report to `meta.output_dir` and return its path."""
    meta.output_dir.mkdir(parents=True, exist_ok=True)
    path = meta.output_dir / STAT_WEIGHTS_FILE
    path.write_text(render_stat_weights(result, meta), encoding="utf-8")
    return path
