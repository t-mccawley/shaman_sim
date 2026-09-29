"""Encounters to simulate."""

from shamansim import Encounter, EncounterType, LevelDelta, Position

ENCOUNTERS: list[Encounter] = [
    # Encounter(
    #     display_name="Boss +3",
    #     description="Single +3 level target that never dies, attacked from behind, 3 minutes.",
    #     encounter_type=EncounterType.SINGLE_TARGET,
    #     duration=180,
    #     enemy_count=1,
    #     enemy_health=1_000_000_000,
    #     enemy_armor=2500,
    #     enemy_level_delta=LevelDelta.PLUS_3,
    #     position=Position.BEHIND,
    # ),
    Encounter(
        display_name="Leveling pulls",
        description="1 same-level mob per pull, fought from the front, for 10 minutes.",
        encounter_type=EncounterType.MULTI_TARGET_LEVELING,
        duration=600,
        enemy_count=1,
        enemy_health=200,
        enemy_armor=300,
        enemy_level_delta=LevelDelta.SAME,
        position=Position.FRONT,
        drink_below_mana_pct=40,
    ),
]
