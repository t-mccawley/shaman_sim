"""Stat weights: stat bumps, paired weighing, selection, and the report."""

import itertools
import math
from collections.abc import Callable
from dataclasses import replace

import numpy as np
import pytest

from shamansim import (
    Character,
    Encounter,
    EncounterType,
    MetaConfig,
    Rotation,
    SimState,
    SpellChoice,
    Stat,
    StatWeightsConfig,
)
from shamansim.experiment.candidates import Candidate
from shamansim.experiment.stat_weights import (
    MeanInterval,
    StatWeight,
    StatWeightsError,
    ranked_by_ep,
    run_stat_weights,
    select_candidate,
    weigh,
    with_stat,
)
from shamansim.model.character import melee_crit_per_agility
from shamansim.model.stats import EffectiveStats
from shamansim.report.stat_weights_html import render_stat_weights
from shamansim.spells.definitions import Spellbook
from shamansim.talents.build import TalentBuild
from shamansim.talents.effects import StatTalents
from tests.conftest import CALC, NO_TALENTS

ENHANCEMENT_31 = TalentBuild.from_url(CALC + "v2-050230031105102251")
META = MetaConfig(seed=3, iterations=6, bootstrap_samples=200)


def _melee_only(s: SimState) -> SpellChoice:
    return None


MELEE_ONLY = Rotation(
    display_name="Melee",
    description="Auto attacks only.",
    encounter_type=EncounterType.SINGLE_TARGET,
    rotation_function=_melee_only,
)


def _config(**overrides: object) -> StatWeightsConfig:
    fields: dict[str, object] = {
        "character": "Test",
        "encounter": "Dummy",
        "rotation": "Melee",
        "talents": CALC + "v2-050230031105102251",
    }
    return StatWeightsConfig(**(fields | overrides))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("stat", "field", "read"),
    [
        (Stat.ATTACK_POWER, "attack_power", lambda c: c.attack_power),
        (Stat.SPELL_POWER, "spell_power", lambda c: c.spell_power.general),
        (Stat.SPIRIT, "spirit", lambda c: c.spirit),
        (Stat.MP5, "mp5", lambda c: c.mp5),
        (Stat.WEAPON_SKILL, "weapon_skill_bonus", lambda c: c.weapon_skill_bonus),
        (Stat.MELEE_CRIT, "melee_crit", lambda c: c.melee_crit),
        (Stat.MELEE_HIT, "melee_hit", lambda c: c.melee_hit),
        (Stat.SPELL_CRIT, "spell_crit", lambda c: c.spell_crit.general),
        (Stat.SPELL_HIT, "spell_hit", lambda c: c.spell_hit.general),
    ],
)
def test_with_stat_adds_to_one_field(
    shaman: Character, stat: Stat, field: str, read: Callable[[Character], float]
) -> None:
    bumped = with_stat(shaman, stat, 5)
    assert read(bumped) == read(shaman) + 5
    assert _changed(shaman, bumped) == [field]


def _changed(a: Character, b: Character) -> list[str]:
    return [f for f in a.__dataclass_fields__ if getattr(a, f) != getattr(b, f)]


def test_gear_intellect_without_sheet_talents_only_adds_intellect_and_mana(
    shaman: Character,
) -> None:
    bumped = with_stat(shaman, Stat.INTELLECT, 10)
    assert bumped.intellect == shaman.intellect + 10
    assert bumped.mana == shaman.mana + 150
    assert _changed(shaman, bumped) == ["intellect", "mana"]


@pytest.mark.parametrize(
    ("sheet", "candidate"),
    [(ENHANCEMENT_31, ENHANCEMENT_31), (ENHANCEMENT_31, NO_TALENTS), (NO_TALENTS, ENHANCEMENT_31)],
)
def test_gear_intellect_is_retalented_like_the_rest_of_the_sheet(
    shaman: Character, sheet: TalentBuild, candidate: TalentBuild
) -> None:
    character = replace(shaman, talents_on_sheet=sheet.url or None)
    before = EffectiveStats.build(character, candidate)
    after = EffectiveStats.build(with_stat(character, Stat.INTELLECT, 10), candidate)
    talents = StatTalents.from_build(candidate)
    gained = 10 * talents.intellect_multiplier
    assert after.intellect - before.intellect == pytest.approx(gained)
    assert after.mana - before.mana == pytest.approx(15 * gained)
    assert after.attack_power - before.attack_power == pytest.approx(
        talents.attack_power_per_intellect * gained
    )
    assert after.spell_power.general - before.spell_power.general == pytest.approx(
        talents.spell_power_per_intellect * gained
    )


def test_gear_strength_adds_attack_power(shaman: Character) -> None:
    bumped = with_stat(shaman, Stat.STRENGTH, 10)
    assert _changed(shaman, bumped) == ["strength", "attack_power"]
    assert bumped.strength == shaman.strength + 10
    assert bumped.attack_power == shaman.attack_power + 20


def test_gear_agility_adds_level_scaled_melee_crit(shaman: Character) -> None:
    bumped = with_stat(shaman, Stat.AGILITY, 10)
    assert _changed(shaman, bumped) == ["agility", "melee_crit"]
    assert bumped.melee_crit == pytest.approx(10 * 0.0717)  # level 40 table value


def test_melee_crit_per_agility_interpolates_agility_per_crit() -> None:
    for level, crit in {25: 0.0971, 40: 0.0717, 50: 0.0600, 60: 0.0508}.items():
        assert melee_crit_per_agility(level) == pytest.approx(crit)
    halfway = (1 / 0.0717 + 1 / 0.0600) / 2
    assert melee_crit_per_agility(45) == pytest.approx(1 / halfway)
    below = 1 / 0.0971 - 5 * (1 / 0.0717 - 1 / 0.0971) / 15
    assert melee_crit_per_agility(20) == pytest.approx(1 / below)
    per_level = [melee_crit_per_agility(level) for level in range(1, 61)]
    assert all(a > b > 0 for a, b in itertools.pairwise(per_level))


def test_talents_scaling_strength_and_agility_change_attack_power_and_crit(
    shaman: Character, monkeypatch: pytest.MonkeyPatch
) -> None:
    character = replace(shaman, strength=100, agility=50)
    plain = EffectiveStats.build(character, NO_TALENTS)
    boosted = StatTalents(strength_multiplier=1.1, agility_multiplier=1.2)
    monkeypatch.setattr(StatTalents, "from_build", classmethod(lambda cls, build: boosted))
    stats = EffectiveStats.build(character, NO_TALENTS)
    assert stats.strength == pytest.approx(110)
    assert stats.agility == pytest.approx(60)
    assert stats.attack_power - plain.attack_power == pytest.approx(20)
    assert stats.melee_crit - plain.melee_crit == pytest.approx(10 * 0.0717)


def test_strength_and_agility_are_simulated_through_attack_power_and_crit(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    candidate = Candidate(
        number=1, character=shaman, encounter=dummy, rotation=MELEE_ONLY, talents=NO_TALENTS
    )
    crit_from_agility = 20 * melee_crit_per_agility(shaman.level)
    steps = {
        Stat.ATTACK_POWER: 50.0,
        Stat.STRENGTH: 25.0,
        Stat.AGILITY: 20.0,
        Stat.MELEE_CRIT: crit_from_agility,
    }
    result = run_stat_weights(candidate, steps, spellbook, META, iterations=4)
    by_stat = {w.stat: w for w in result.weights}
    assert by_stat[Stat.STRENGTH].ep.mean == pytest.approx(2.0)
    agility, crit = by_stat[Stat.AGILITY], by_stat[Stat.MELEE_CRIT]
    assert agility.dps_per_point.mean * 20 == pytest.approx(
        crit.dps_per_point.mean * crit_from_agility
    )


def test_weigh_normalizes_to_attack_power() -> None:
    baseline = np.random.default_rng(0).normal(100.0, 10.0, size=400)
    totals = {
        Stat.ATTACK_POWER: baseline + 50 * 12.0,
        Stat.INTELLECT: baseline + 20 * 36.0,
        Stat.SPIRIT: baseline.copy(),
    }
    steps = {Stat.ATTACK_POWER: 50.0, Stat.INTELLECT: 20.0, Stat.SPIRIT: 20.0}
    base, weights = weigh(baseline, totals, steps, META)
    by_stat = {w.stat: w for w in weights}
    assert by_stat[Stat.ATTACK_POWER].dps_per_point.mean == pytest.approx(12.0)
    assert by_stat[Stat.ATTACK_POWER].ep.mean == pytest.approx(1.0)
    assert by_stat[Stat.INTELLECT].ep.mean == pytest.approx(3.0)
    assert by_stat[Stat.SPIRIT].ep.mean == 0.0
    assert not by_stat[Stat.SPIRIT].dps_per_point.excludes_zero
    assert base.median == pytest.approx(float(np.median(baseline)))


def test_weigh_uses_the_mean_of_lumpy_differences() -> None:
    # Most iterations unchanged (overkill), a few gain a whole kill: the median is 0.
    baseline = np.full(100, 30.0)
    lumpy = baseline.copy()
    lumpy[:20] += 1.0
    totals = {Stat.ATTACK_POWER: baseline + 1.0, Stat.SPELL_CRIT: lumpy}
    _, weights = weigh(baseline, totals, {Stat.ATTACK_POWER: 1.0, Stat.SPELL_CRIT: 1.0}, META)
    assert weights[1].dps_per_point.mean == pytest.approx(0.2)


def test_paired_seeds_cancel_noise_for_unused_stats(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    candidate = Candidate(
        number=1, character=shaman, encounter=dummy, rotation=MELEE_ONLY, talents=NO_TALENTS
    )
    steps = {Stat.ATTACK_POWER: 50.0, Stat.SPELL_POWER: 50.0, Stat.SPIRIT: 20.0}
    seen: list[str] = []
    result = run_stat_weights(
        candidate, steps, spellbook, META, iterations=4, on_done=lambda label, _: seen.append(label)
    )
    by_stat = {w.stat: w for w in result.weights}
    assert by_stat[Stat.ATTACK_POWER].dps_per_point.low > 0
    assert by_stat[Stat.ATTACK_POWER].ep.mean == pytest.approx(1.0)
    for unused in (Stat.SPELL_POWER, Stat.SPIRIT):
        assert by_stat[unused].dps_per_point == MeanInterval(0.0, 0.0, 0.0)
    assert seen == ["Baseline", "Attack power +50", "Spell power +50", "Spirit +20"]


def test_select_candidate_matches_rotation_to_encounter_type(
    shaman: Character, dummy: Encounter
) -> None:
    leveling = replace(MELEE_ONLY, encounter_type=EncounterType.MULTI_TARGET_LEVELING)
    candidate = select_candidate(_config(), [shaman], [dummy], [leveling, MELEE_ONLY])
    assert candidate.rotation is MELEE_ONLY
    assert candidate.talents.url == ENHANCEMENT_31.url


def test_select_candidate_lists_available_names(shaman: Character, dummy: Encounter) -> None:
    with pytest.raises(StatWeightsError, match=r"character 'Nope' not found; available: 'Test'"):
        select_candidate(_config(character="Nope"), [shaman], [dummy], [MELEE_ONLY])
    with pytest.raises(StatWeightsError, match="is ambiguous"):
        select_candidate(_config(), [shaman, shaman], [dummy], [MELEE_ONLY])


def test_config_requires_attack_power_and_whole_weapon_skill() -> None:
    with pytest.raises(ValueError, match="ATTACK_POWER"):
        _config(steps={Stat.SPIRIT: 10})
    with pytest.raises(ValueError, match="whole number"):
        _config(steps={Stat.ATTACK_POWER: 50, Stat.WEAPON_SKILL: 2.5})
    with pytest.raises(ValueError, match="positive"):
        _config(steps={Stat.ATTACK_POWER: 0})


def _weight(stat: Stat, ep: float) -> StatWeight:
    return StatWeight(
        stat=stat, step=1.0, dps_per_point=MeanInterval(ep, ep, ep), ep=MeanInterval(ep, ep, ep)
    )


def test_ranked_by_ep_puts_undefined_last() -> None:
    ranked = ranked_by_ep(
        [_weight(Stat.SPIRIT, math.nan), _weight(Stat.ATTACK_POWER, 1.0), _weight(Stat.MP5, 2.0)]
    )
    assert [w.stat for w in ranked] == [Stat.MP5, Stat.ATTACK_POWER, Stat.SPIRIT]


def test_report_shows_every_stat_and_both_unit_charts(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    candidate = Candidate(
        number=1, character=shaman, encounter=dummy, rotation=MELEE_ONLY, talents=NO_TALENTS
    )
    steps = {Stat.ATTACK_POWER: 50.0, Stat.MELEE_CRIT: 2.0}
    result = run_stat_weights(candidate, steps, spellbook, META, iterations=3)
    page = render_stat_weights(result, META)
    assert "<title>ShamanSim Stat Weights</title>" in page
    assert "DpS per point (mean" in page
    assert "DpS per 1% (mean" in page
    assert "Attack power" in page and "Melee crit" in page
    assert "Reference: EP = 1 by definition." in page
