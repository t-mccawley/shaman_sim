"""Static spell-use detection in rotation functions."""

from shamansim import SimState, SpellChoice, SpellId
from shamansim.model.rotation_analysis import used_spells


def _guarded(s: SimState) -> SpellChoice:
    target = s.target
    if target is not None and target.stormstruck and s.spells.earth_shock.ready:
        return s.spells.earth_shock
    return s.spells.stormstrike


def _known_only(s: SimState) -> SpellChoice:
    if s.spells.rage_of_the_farseer.known:
        return SpellId.LIGHTNING_BOLT
    return s.spells.flame_shock


def test_guarded_references_count_as_use() -> None:
    assert used_spells(_guarded) == {SpellId.EARTH_SHOCK, SpellId.STORMSTRIKE}


def test_known_checks_do_not_count_and_spell_ids_do() -> None:
    assert used_spells(_known_only) == {SpellId.LIGHTNING_BOLT, SpellId.FLAME_SHOCK}


def test_known_checked_spell_is_excluded_even_when_cast() -> None:
    def adaptive(s: SimState) -> SpellChoice:
        return s.spells.stormstrike if s.spells.stormstrike.known else None

    assert used_spells(adaptive) == frozenset()
