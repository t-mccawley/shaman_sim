"""Engine behaviour."""

import random

import numpy as np
import pytest

from shamansim import (
    Character,
    Encounter,
    EncounterType,
    Rotation,
    RotationFunction,
    SimState,
    SpellChoice,
    SpellId,
    Water,
    WeaponImbue,
)
from shamansim.engine.simulator import MELEE, WINDFURY_ATTACK, RejectReason, Simulation
from shamansim.engine.state import UnavailableSpellError
from shamansim.spells.definitions import Spellbook
from shamansim.talents.build import TalentBuild
from tests.conftest import CALC, NO_TALENTS, WEAPON

ENHANCEMENT_31 = TalentBuild.from_url(CALC + "v2-050230031105102251")


def _rotation(
    function: RotationFunction,
    imbue: WeaponImbue = WeaponImbue.NONE,
    kind: EncounterType = EncounterType.SINGLE_TARGET,
) -> Rotation:
    return Rotation(
        display_name="t",
        description="",
        encounter_type=kind,
        rotation_function=function,
        weapon_imbue=imbue,
    )


def _sim(
    character: Character,
    encounter: Encounter,
    rotation: Rotation,
    spellbook: Spellbook,
    talents: TalentBuild = NO_TALENTS,
) -> Simulation:
    return Simulation(
        character,
        encounter,
        talents,
        rotation,
        spellbook,
        tick_seconds=0.1,
        peak_warmup_seconds=5.0,
    )


def _idle(s: SimState) -> SpellChoice:
    return None


def test_same_seed_is_reproducible(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    sim = _sim(shaman, dummy, _rotation(_idle), spellbook)
    assert sim.run(random.Random(3)).total_dps == sim.run(random.Random(3)).total_dps


def test_white_swings_match_attack_table(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    sim = _sim(shaman, dummy, _rotation(_idle), spellbook)
    rng = random.Random(1)
    per_swing = []
    for _ in range(300):
        result = sim.run(rng)
        per_swing.append(result.damage_by_source[MELEE] / result.casts[MELEE])
    swing = WEAPON.min_damage + WEAPON.speed * shaman.attack_power / 14
    # Same level: 5% miss, 5% dodge, 10% glancing at 91-99% damage, no crit.
    expected = swing * (0.80 + 0.10 * 0.95)
    assert np.mean(per_swing) == pytest.approx(expected, rel=0.01)


def test_windfury_procs_on_a_fifth_of_landed_hits(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    sim = _sim(shaman, dummy, _rotation(_idle, WeaponImbue.WINDFURY), spellbook)
    rng = random.Random(2)
    procs = swings = 0
    for _ in range(300):
        result = sim.run(rng)
        procs += result.casts.get(WINDFURY_ATTACK, 0) // 2
        swings += result.casts[MELEE]
    # Windfury attacks cannot proc Windfury; 90% of swings land.
    assert procs / (swings * 0.90) == pytest.approx(0.20, abs=0.02)


def test_rockbiter_adds_attack_power(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    sim = _sim(shaman, dummy, _rotation(_idle, WeaponImbue.ROCKBITER), spellbook)
    assert sim.attack_power == pytest.approx(700 + 355)


def test_shocks_share_one_cooldown(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    def alternate(s: SimState) -> SpellChoice:
        sb = s.spells
        if not s.target or not s.target.has_dot("Flame Shock"):
            return sb.flame_shock if sb.flame_shock.ready else None
        return sb.earth_shock if sb.earth_shock.ready else None

    result = _sim(shaman, dummy, _rotation(alternate), spellbook).run(random.Random(0))
    shocks = result.casts["Flame Shock (Rank 4)"] + result.casts["Earth Shock (Rank 5)"]
    assert shocks == 11  # one per 6 s over 60 s, starting at 0


def test_fire_nova_needs_a_fire_totem(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    def nova(s: SimState) -> SpellChoice:
        return s.spells.fire_nova

    result = _sim(shaman, dummy, _rotation(nova), spellbook).run(random.Random(0))
    assert result.blocked_seconds[f"Fire Nova: {RejectReason.NO_FIRE_TOTEM}"] > 55


def test_searing_totem_attacks_on_its_interval(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    def totem(s: SimState) -> SpellChoice:
        return s.spells.searing_totem if s.fire_totem is None else None

    sim = _sim(shaman, dummy, _rotation(totem), spellbook)
    result = sim.run(random.Random(0))
    assert result.casts["Searing Totem (Rank 4)"] == 2  # 45 s totems over 60 s
    assert result.damage_by_source["Searing Totem"] > 0


def test_casting_delays_melee_swings(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    def bolt(s: SimState) -> SpellChoice:
        return s.spells.lightning_bolt

    idle = _sim(shaman, dummy, _rotation(_idle), spellbook).run(random.Random(0))
    casting = _sim(shaman, dummy, _rotation(bolt), spellbook).run(random.Random(0))
    assert casting.casts[MELEE] < idle.casts[MELEE]


def test_stormstrike_empowers_next_earth_shock(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    seen: list[bool] = []

    def strike(s: SimState) -> SpellChoice:
        sb = s.spells
        if sb.stormstrike.ready:
            return sb.stormstrike
        if s.target is not None and s.target.stormstruck and sb.earth_shock.ready:
            seen.append(True)
            return sb.earth_shock
        return None

    sim = _sim(shaman, dummy, _rotation(strike), spellbook, ENHANCEMENT_31)
    result = sim.run(random.Random(0))
    assert result.casts["Stormstrike (Rank 1)"] >= 7
    assert result.casts["Earth Shock (Rank 5)"] == len(seen) > 0


def test_untalented_spell_raises(shaman: Character, dummy: Encounter, spellbook: Spellbook) -> None:
    def strike(s: SimState) -> SpellChoice:
        return s.spells.stormstrike if s.spells.stormstrike.ready else None

    sim = _sim(shaman, dummy, _rotation(strike), spellbook)
    with pytest.raises(UnavailableSpellError, match="requires the Stormstrike talent"):
        sim.run(random.Random(0))


def test_casts_highest_known_rank(
    shaman: Character, dummy: Encounter, spellbook: Spellbook
) -> None:
    def bolt(s: SimState) -> SpellChoice:
        return SpellId.LIGHTNING_BOLT

    result = _sim(shaman, dummy, _rotation(bolt), spellbook).run(random.Random(0))
    assert "Lightning Bolt (Rank 7)" in result.casts


def test_leveling_drinks_between_pulls(spellbook: Spellbook) -> None:
    character = Character(
        display_name="c",
        level=40,
        intellect=100,
        spirit=100,
        mana=600,
        attack_power=700,
        weapon=WEAPON,
        water=Water.MELON_JUICE,
    )
    encounter = Encounter(
        display_name="e",
        description="",
        duration=300,
        enemy_count=1,
        enemy_health=800,
        encounter_type=EncounterType.MULTI_TARGET_LEVELING,
        drink_below_mana_pct=50,
    )

    def bolt(s: SimState) -> SpellChoice:
        return s.spells.lightning_bolt

    rotation = _rotation(bolt, kind=EncounterType.MULTI_TARGET_LEVELING)
    result = _sim(character, encounter, rotation, spellbook).run(random.Random(0))
    assert result.enemies_killed > 3
    assert result.drinking_time > 0
