"""Talent effects on damage, cost, timing, and stats.

Per-rank values come from WoW Forever talent descriptions (Wowhead).
Talents that change character-sheet stats are in StatTalents; all others in
TalentModifiers.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Final

from shamansim.core.enums import School
from shamansim.spells.definitions import SpellId
from shamansim.spells.mechanics import SPELL_MECHANICS
from shamansim.talents.build import TalentBuild

SHOCKS: Final = (SpellId.EARTH_SHOCK, SpellId.FLAME_SHOCK, SpellId.FROST_SHOCK)
TOTEMS: Final = (SpellId.SEARING_TOTEM, SpellId.MAGMA_TOTEM)
FIRE_TOTEM_DAMAGE: Final = (SpellId.FLAME_SHOCK, SpellId.FIRE_NOVA, SpellId.LAVA_BURST, *TOTEMS)
MAGIC_DAMAGE_SCHOOLS: Final = (School.NATURE, School.FIRE, School.FROST)

# Per-rank values, index = rank - 1.
ELEMENTAL_ALACRITY_SECONDS: Final = (0.17, 0.33, 0.50)
LIGHTNING_OVERLOAD_CHANCE: Final = (0.03, 0.07, 0.10)
MENTAL_DEXTERITY_AP_PER_INT: Final = (0.33, 0.67, 1.00)
MENTAL_QUICKNESS_SP_PER_INT: Final = (0.15, 0.30)
ROCKBITER_BONUS: Final = (0.07, 0.13, 0.20)
WINDFURY_BONUS: Final = (0.13, 0.27, 0.40)
IMBUE_DAMAGE_BONUS: Final = (0.05, 0.10, 0.15)
IMPROVED_STORMSTRIKE_CHANCE: Final = (0.5, 1.0)
MINDFULNESS_REGEN: Final = (1 / 6, 1 / 3, 0.5)

# Talents with no effect on simulated damage.
NO_DAMAGE_EFFECT: Final = frozenset(
    {
        "Elemental Warding",
        "Eye of the Storm",
        "Elemental Reach",
        "Earthbound",
        "Earth's Grasp",
        "Guardian Totems",
        "Improved Ghost Wolf",
        "Improved Lightning Shield",
        "Anticipation",
        "Toughness",
        "Spirit Weapons",
        "Improved Healing Wave",
        "Natural Grace",
        "Improved Reincarnation",
        "Ancestral Healing",
        "Healing Focus",
        "Tidal Mastery",
        "Restorative Totems",
        "Healing Way",
        "Purification",
        "Riptide",
    }
)

# Talents modeled by TalentModifiers or StatTalents.
_IMPLEMENTED: Final = frozenset(
    {
        "Convection",
        "Concussion",
        "Reverberation",
        "Call of Flame",
        "Elemental Devastation",
        "Elemental Focus",
        "Elemental Alacrity",
        "Improved Fire Nova",
        "Call of Thunder",
        "Lightning Overload",
        "Elemental Fury",
        "Lava Burst",
        "Thundering Strikes",
        "Ancestral Knowledge",
        "Mental Dexterity",
        "Elemental Weapons",
        "Shamanistic Focus",
        "Flurry",
        "Stormstrike",
        "Mental Quickness",
        "Improved Stormstrike",
        "Maelstrom Weapon",
        "Rage of the Farseer",
        "Totemic Focus",
        "Mindfulness",
        "Tidal Focus",
    }
)


def _per_rank(values: tuple[float, ...], rank: int) -> float:
    return values[rank - 1] if rank else 0.0


@dataclass(frozen=True, slots=True, kw_only=True)
class StatTalents:
    """Talents that change character-sheet stats. Percent values in percent."""

    crit_pct: float = 0.0
    intellect_multiplier: float = 1.0
    attack_power_per_intellect: float = 0.0
    spell_power_per_intellect: float = 0.0

    @classmethod
    def from_build(cls, build: TalentBuild) -> "StatTalents":
        """Stat bonuses of `build`."""
        r = build.rank
        return cls(
            crit_pct=1.0 * r("Thundering Strikes"),
            intellect_multiplier=1.0 + 0.02 * r("Ancestral Knowledge"),
            attack_power_per_intellect=_per_rank(
                MENTAL_DEXTERITY_AP_PER_INT, r("Mental Dexterity")
            ),
            spell_power_per_intellect=_per_rank(MENTAL_QUICKNESS_SP_PER_INT, r("Mental Quickness")),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class TalentModifiers:
    """Aggregated non-stat talent effects. Percent values are in percent."""

    hit_pct: float = 0.0
    crit_pct_spell: dict[SpellId, float] = field(default_factory=dict)
    spell_crit_damage_bonus: dict[School, float] = field(default_factory=dict)
    damage_multiplier_spell: dict[SpellId, float] = field(default_factory=dict)
    cost_multiplier_spell: dict[SpellId, float] = field(default_factory=dict)
    cast_time_reduction: dict[SpellId, float] = field(default_factory=dict)
    cooldown_reduction: dict[SpellId, float] = field(default_factory=dict)
    granted_spells: frozenset[SpellId] = frozenset()
    clearcasting_chance: float = 0.0
    lightning_overload_chance: float = 0.0
    elemental_devastation_crit_pct: float = 0.0
    flurry_haste: float = 0.0
    rockbiter_multiplier: float = 1.0
    windfury_multiplier: float = 1.0
    imbue_damage_multiplier: float = 1.0
    maelstrom_per_stack: float = 0.0
    improved_stormstrike_chance: float = 0.0
    casting_regen: float = 0.0
    unimplemented: tuple[str, ...] = ()

    @classmethod
    def from_build(cls, build: TalentBuild) -> "TalentModifiers":
        """Compute modifiers from talent ranks."""
        r = build.rank
        damage: defaultdict[SpellId, float] = defaultdict(lambda: 1.0)
        for spell in (SpellId.LIGHTNING_BOLT, SpellId.CHAIN_LIGHTNING, SpellId.EARTH_SHOCK):
            damage[spell] *= 1.0 + 0.01 * r("Concussion")
        for spell in FIRE_TOTEM_DAMAGE:
            damage[spell] *= 1.0 + 0.05 * r("Call of Flame")
        damage[SpellId.FIRE_NOVA] *= 1.0 + 0.10 * r("Improved Fire Nova")

        cost: defaultdict[SpellId, float] = defaultdict(lambda: 1.0)
        for spell in (*SHOCKS, SpellId.LIGHTNING_BOLT, SpellId.LAVA_BURST, SpellId.CHAIN_LIGHTNING):
            cost[spell] *= 1.0 - 0.02 * r("Convection")
        for spell in SHOCKS:
            cost[spell] *= 1.0 - 0.45 * r("Shamanistic Focus")
        for spell in TOTEMS:
            cost[spell] *= 1.0 - 0.05 * r("Totemic Focus")

        alacrity = _per_rank(ELEMENTAL_ALACRITY_SECONDS, r("Elemental Alacrity"))
        cooldown = {s: 0.2 * r("Reverberation") for s in SHOCKS}
        cooldown[SpellId.FIRE_NOVA] = 2.0 * r("Improved Fire Nova")
        rank_ew = r("Elemental Weapons")
        granted = frozenset(
            m.spell_id
            for m in SPELL_MECHANICS.values()
            if m.granted_by_talent is not None and r(m.granted_by_talent) > 0
        )
        known = NO_DAMAGE_EFFECT | _IMPLEMENTED
        return cls(
            hit_pct=1.0 * r("Tidal Focus"),
            crit_pct_spell={
                SpellId.LIGHTNING_BOLT: 3.0 * r("Call of Thunder"),
                SpellId.CHAIN_LIGHTNING: 3.0 * r("Call of Thunder"),
            },
            spell_crit_damage_bonus=dict.fromkeys(MAGIC_DAMAGE_SCHOOLS, 0.2 * r("Elemental Fury")),
            damage_multiplier_spell=dict(damage),
            cost_multiplier_spell=dict(cost),
            cast_time_reduction={
                SpellId.LIGHTNING_BOLT: alacrity,
                SpellId.CHAIN_LIGHTNING: alacrity,
                SpellId.LAVA_BURST: alacrity,
            },
            cooldown_reduction=cooldown,
            granted_spells=granted,
            clearcasting_chance=0.10 * r("Elemental Focus"),
            lightning_overload_chance=_per_rank(LIGHTNING_OVERLOAD_CHANCE, r("Lightning Overload")),
            elemental_devastation_crit_pct=3.0 * r("Elemental Devastation"),
            flurry_haste=0.05 * r("Flurry"),
            rockbiter_multiplier=1.0 + _per_rank(ROCKBITER_BONUS, rank_ew),
            windfury_multiplier=1.0 + _per_rank(WINDFURY_BONUS, rank_ew),
            imbue_damage_multiplier=1.0 + _per_rank(IMBUE_DAMAGE_BONUS, rank_ew),
            maelstrom_per_stack=0.04 * r("Maelstrom Weapon"),
            improved_stormstrike_chance=_per_rank(
                IMPROVED_STORMSTRIKE_CHANCE, r("Improved Stormstrike")
            ),
            casting_regen=_per_rank(MINDFULNESS_REGEN, r("Mindfulness")),
            unimplemented=tuple(sorted(name for name in build.ranks if name not in known)),
        )
