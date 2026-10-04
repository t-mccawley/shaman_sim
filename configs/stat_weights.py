"""Stat weights: `shamansim stat-weights` writes results/stat_weights_results.html.

Pick one character, encounter, and rotation by display name (from the other
config files) and one talent calculator link. Each stat in `steps` is raised by
its step and simulated against the unmodified character; the report shows DpS
per point (per 1% for percent stats) and equivalence points relative to one
attack power. Remove stats from `steps` to skip them; bigger steps reduce noise
but blur caps (such as hit). Attack power is required.

Values per point can depend on the step: against low-health enemies, extra
damage pays off in jumps as hits start killing in fewer swings. Compare stats
at steps worth about the same damage.
"""

from shamansim import Stat, StatWeightsConfig

# L20
# STAT_WEIGHTS = StatWeightsConfig(
#     character="L20",
#     encounter="L20 Leveling pulls",
#     rotation="Shocks RB",
#     talents="https://www.wowhead.com/forever/talent-calc/shaman/v2-050032001_t0/1BEFj", # L20
#     iterations=1000,
#     steps={
#         Stat.ATTACK_POWER: 50,
#         Stat.STRENGTH: 25,  # = 50 attack power, matching the attack power step
#         Stat.AGILITY: 20,
#         Stat.SPELL_POWER: 50,
#         Stat.INTELLECT: 20,
#         Stat.SPIRIT: 20,
#         Stat.MP5: 10,
#         Stat.WEAPON_SKILL: 5,
#         Stat.MELEE_CRIT: 2,
#         Stat.MELEE_HIT: 2,
#         Stat.SPELL_CRIT: 2,
#         Stat.SPELL_HIT: 2,
#     },
# )

# L30
STAT_WEIGHTS = StatWeightsConfig(
    character="L30",
    encounter="L30 Leveling pulls",
    rotation="Stormstrike WF",
    talents="https://www.wowhead.com/forever/talent-calc/shaman/v2-0510320310051_t0/1BEFjHcNp", # L30
    iterations=1000,
    steps={
        Stat.ATTACK_POWER: 50,
        Stat.STRENGTH: 25,  # = 50 attack power, matching the attack power step
        Stat.AGILITY: 20,
        Stat.SPELL_POWER: 50,
        Stat.INTELLECT: 20,
        Stat.SPIRIT: 20,
        Stat.MP5: 10,
        Stat.WEAPON_SKILL: 5,
        Stat.MELEE_CRIT: 2,
        Stat.MELEE_HIT: 2,
        Stat.SPELL_CRIT: 2,
        Stat.SPELL_HIT: 2,
    },
)
