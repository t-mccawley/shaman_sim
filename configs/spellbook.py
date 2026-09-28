"""Spell and weapon imbue ranks as shown in game (trainer / tooltip values).

Coefficients are calculated from these values; audit them with `shamansim spellbook`.
DoTs: DotData(damage=total, duration=seconds, ticks=count).
Totems: min/max damage per attack; TotemData(duration, attack_interval).
Imbue `value`: Rockbiter = attack power; Flametongue = X in 'X / 100 * weapon speed'
Fire damage per hit; Frostbrand = Frost damage per proc; Windfury = attack power
of each extra attack.
Pre-filled from Wowhead's Forever database (levels 1-60); set
`confirmed_in_game_date` on each rank once checked against the in-game trainer.
Not in tooltips (from wowsims): Searing Totem attack interval, Flame Shock tick count.
Talent spells (Stormstrike, Lava Burst, Rage of the Farseer) need their talent.
"""
# ruff: noqa: E501
# fmt: off

from shamansim import BuffData, DotData, ImbueRank, SpellId, SpellRank, TotemData, WeaponImbue

SPELL_RANKS: dict[SpellId, list[SpellRank]] = {
    SpellId.STORMSTRIKE: [
        SpellRank(rank=1, level=40, mana_cost=125, cooldown=8, wowhead_id=17364),
    ],
    SpellId.LIGHTNING_BOLT: [
        SpellRank(rank=1, level=1, min_damage=15, max_damage=17, mana_cost=15, cast_time=1.5, wowhead_id=403),
        SpellRank(rank=2, level=8, min_damage=29, max_damage=34, mana_cost=30, cast_time=2, wowhead_id=529),
        SpellRank(rank=3, level=14, min_damage=44, max_damage=52, mana_cost=45, cast_time=2.5, wowhead_id=548),
        SpellRank(rank=4, level=20, min_damage=55, max_damage=63, mana_cost=60, cast_time=2.5, wowhead_id=915),
        SpellRank(rank=5, level=26, min_damage=71, max_damage=80, mana_cost=85, cast_time=2.5, wowhead_id=943),
        SpellRank(rank=6, level=32, min_damage=108, max_damage=122, mana_cost=110, cast_time=2.5, wowhead_id=6041),
        SpellRank(rank=7, level=38, min_damage=142, max_damage=160, mana_cost=135, cast_time=2.5, wowhead_id=10391),
        SpellRank(rank=8, level=44, min_damage=158, max_damage=176, mana_cost=160, cast_time=2.5, wowhead_id=10392),
        SpellRank(rank=9, level=50, min_damage=173, max_damage=193, mana_cost=190, cast_time=2.5, wowhead_id=15207),
        SpellRank(rank=10, level=56, min_damage=191, max_damage=213, mana_cost=220, cast_time=2.5, wowhead_id=15208),
    ],
    SpellId.CHAIN_LIGHTNING: [
        SpellRank(rank=1, level=32, min_damage=85, max_damage=97, mana_cost=225, cast_time=2, cooldown=6, wowhead_id=421),
        SpellRank(rank=2, level=40, min_damage=97, max_damage=109, mana_cost=305, cast_time=2, cooldown=6, wowhead_id=930),
        SpellRank(rank=3, level=48, min_damage=109, max_damage=122, mana_cost=390, cast_time=2, cooldown=6, wowhead_id=2860),
        SpellRank(rank=4, level=56, min_damage=120, max_damage=134, mana_cost=485, cast_time=2, cooldown=6, wowhead_id=10605),
    ],
    SpellId.LAVA_BURST: [
        SpellRank(rank=1, level=40, min_damage=150, max_damage=192, mana_cost=165, cast_time=2.5, cooldown=10, wowhead_id=408490),
        SpellRank(rank=2, level=50, min_damage=180, max_damage=230, mana_cost=230, cast_time=2.5, cooldown=10, wowhead_id=1238299),
        SpellRank(rank=3, level=60, min_damage=203, max_damage=258, mana_cost=265, cast_time=2.5, cooldown=10, wowhead_id=1238300),
    ],
    SpellId.EARTH_SHOCK: [
        SpellRank(rank=1, level=4, min_damage=20, max_damage=22, mana_cost=30, cooldown=6, wowhead_id=8042),
        SpellRank(rank=2, level=8, min_damage=36, max_damage=38, mana_cost=50, cooldown=6, wowhead_id=8044),
        SpellRank(rank=3, level=14, min_damage=52, max_damage=55, mana_cost=85, cooldown=6, wowhead_id=8045),
        SpellRank(rank=4, level=24, min_damage=84, max_damage=89, mana_cost=145, cooldown=6, wowhead_id=8046),
        SpellRank(rank=5, level=36, min_damage=135, max_damage=142, mana_cost=240, cooldown=6, wowhead_id=10412),
        SpellRank(rank=6, level=48, min_damage=207, max_damage=219, mana_cost=345, cooldown=6, wowhead_id=10413),
        SpellRank(rank=7, level=60, min_damage=303, max_damage=318, mana_cost=450, cooldown=6, wowhead_id=10414),
    ],
    SpellId.FLAME_SHOCK: [
        SpellRank(rank=1, level=10, min_damage=24, max_damage=24, mana_cost=55, cooldown=6, dot=DotData(damage=28, duration=12, ticks=4), wowhead_id=8050),
        SpellRank(rank=2, level=18, min_damage=38, max_damage=38, mana_cost=95, cooldown=6, dot=DotData(damage=32, duration=12, ticks=4), wowhead_id=8052),
        SpellRank(rank=3, level=28, min_damage=49, max_damage=49, mana_cost=160, cooldown=6, dot=DotData(damage=56, duration=12, ticks=4), wowhead_id=8053),
        SpellRank(rank=4, level=40, min_damage=89, max_damage=89, mana_cost=250, cooldown=6, dot=DotData(damage=84, duration=12, ticks=4), wowhead_id=10447),
        SpellRank(rank=5, level=52, min_damage=137, max_damage=137, mana_cost=345, cooldown=6, dot=DotData(damage=136, duration=12, ticks=4), wowhead_id=10448),
        SpellRank(rank=6, level=60, min_damage=181, max_damage=181, mana_cost=410, cooldown=6, dot=DotData(damage=176, duration=12, ticks=4), wowhead_id=29228),
    ],
    SpellId.FROST_SHOCK: [
        SpellRank(rank=1, level=20, min_damage=68, max_damage=73, mana_cost=115, cooldown=6, wowhead_id=8056),
        SpellRank(rank=2, level=34, min_damage=126, max_damage=135, mana_cost=225, cooldown=6, wowhead_id=8058),
        SpellRank(rank=3, level=46, min_damage=190, max_damage=201, mana_cost=325, cooldown=6, wowhead_id=10472),
        SpellRank(rank=4, level=58, min_damage=284, max_damage=300, mana_cost=430, cooldown=6, wowhead_id=10473),
    ],
    SpellId.FIRE_NOVA: [
        SpellRank(rank=1, level=12, min_damage=54, max_damage=62, mana_cost=95, cooldown=10, wowhead_id=408341),
        SpellRank(rank=2, level=22, min_damage=110, max_damage=124, mana_cost=170, cooldown=10, wowhead_id=408342),
        SpellRank(rank=3, level=32, min_damage=195, max_damage=219, mana_cost=280, cooldown=10, wowhead_id=408343),
        SpellRank(rank=4, level=42, min_damage=295, max_damage=331, mana_cost=395, cooldown=10, wowhead_id=408344),
        SpellRank(rank=5, level=52, min_damage=413, max_damage=459, mana_cost=520, cooldown=10, wowhead_id=408345),
    ],
    SpellId.SEARING_TOTEM: [
        SpellRank(rank=1, level=10, min_damage=9, max_damage=11, mana_cost=25, totem=TotemData(duration=30, attack_interval=2.5), wowhead_id=3599),
        SpellRank(rank=2, level=20, min_damage=13, max_damage=17, mana_cost=45, totem=TotemData(duration=35, attack_interval=2.5), wowhead_id=6363),
        SpellRank(rank=3, level=30, min_damage=19, max_damage=25, mana_cost=75, totem=TotemData(duration=40, attack_interval=2.5), wowhead_id=6364),
        SpellRank(rank=4, level=40, min_damage=26, max_damage=34, mana_cost=110, totem=TotemData(duration=45, attack_interval=2.5), wowhead_id=6365),
        SpellRank(rank=5, level=50, min_damage=33, max_damage=45, mana_cost=145, totem=TotemData(duration=50, attack_interval=2.5), wowhead_id=10437),
        SpellRank(rank=6, level=60, min_damage=40, max_damage=54, mana_cost=170, totem=TotemData(duration=55, attack_interval=2.5), wowhead_id=10438),
    ],
    SpellId.MAGMA_TOTEM: [
        SpellRank(rank=1, level=26, min_damage=20, max_damage=20, mana_cost=230, totem=TotemData(duration=20, attack_interval=2), wowhead_id=8190),
        SpellRank(rank=2, level=36, min_damage=35, max_damage=35, mana_cost=360, totem=TotemData(duration=20, attack_interval=2), wowhead_id=10585),
        SpellRank(rank=3, level=46, min_damage=52, max_damage=52, mana_cost=500, totem=TotemData(duration=20, attack_interval=2), wowhead_id=10586),
        SpellRank(rank=4, level=56, min_damage=73, max_damage=73, mana_cost=650, totem=TotemData(duration=20, attack_interval=2), wowhead_id=10587),
    ],
    SpellId.RAGE_OF_THE_FARSEER: [
        SpellRank(rank=1, level=1, cooldown=180, buff=BuffData(duration=25, attack_speed_pct=30), wowhead_id=425336),
    ],
}

IMBUE_RANKS: dict[WeaponImbue, list[ImbueRank]] = {
    WeaponImbue.ROCKBITER: [
        ImbueRank(rank=1, level=1, value=50, mana_cost=15, wowhead_id=8017),
        ImbueRank(rank=2, level=8, value=79, mana_cost=25, wowhead_id=8018),
        ImbueRank(rank=3, level=16, value=118, mana_cost=50, wowhead_id=8019),
        ImbueRank(rank=4, level=24, value=194, mana_cost=75, wowhead_id=10399),
        ImbueRank(rank=5, level=34, value=355, mana_cost=100, wowhead_id=16314),
        ImbueRank(rank=6, level=44, value=522, mana_cost=125, wowhead_id=16315),
        ImbueRank(rank=7, level=54, value=686, mana_cost=150, wowhead_id=16316),
    ],
    WeaponImbue.FLAMETONGUE: [
        ImbueRank(rank=1, level=10, value=440, mana_cost=30, wowhead_id=8024),
        ImbueRank(rank=2, level=18, value=653, mana_cost=55, wowhead_id=8027),
        ImbueRank(rank=3, level=26, value=1052, mana_cost=80, wowhead_id=8030),
        ImbueRank(rank=4, level=36, value=1728, mana_cost=105, wowhead_id=16339),
        ImbueRank(rank=5, level=46, value=2372, mana_cost=130, wowhead_id=16341),
        ImbueRank(rank=6, level=56, value=3122, mana_cost=155, wowhead_id=16342),
    ],
    WeaponImbue.FROSTBRAND: [
        ImbueRank(rank=1, level=20, value=45, mana_cost=60, wowhead_id=8033),
        ImbueRank(rank=2, level=28, value=72, mana_cost=85, wowhead_id=8038),
        ImbueRank(rank=3, level=38, value=117, mana_cost=110, wowhead_id=10456),
        ImbueRank(rank=4, level=48, value=159, mana_cost=135, wowhead_id=16355),
        ImbueRank(rank=5, level=58, value=203, mana_cost=160, wowhead_id=16356),
    ],
    WeaponImbue.WINDFURY: [
        ImbueRank(rank=1, level=30, value=104, mana_cost=90, wowhead_id=8232),
        ImbueRank(rank=2, level=40, value=221, mana_cost=115, wowhead_id=8235),
        ImbueRank(rank=3, level=50, value=315, mana_cost=140, wowhead_id=10486),
        ImbueRank(rank=4, level=60, value=433, mana_cost=165, wowhead_id=16362),
    ],
}
