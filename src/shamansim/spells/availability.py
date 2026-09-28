"""Which rank of a spell or imbue a character uses, or why it cannot."""

from dataclasses import dataclass

from shamansim.core.enums import WeaponImbue
from shamansim.spells.definitions import (
    ImbueRank,
    SpellDefinition,
    SpellId,
    SpellRank,
    imbue_rank_for_level,
)


@dataclass(frozen=True, slots=True)
class RankResolution:
    """The rank to cast, or the reason there is none."""

    rank: SpellRank | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ImbueResolution:
    """The imbue rank to apply, or the reason there is none."""

    rank: ImbueRank | None
    reason: str | None = None


def resolve_imbue(imbue: WeaponImbue, ranks: tuple[ImbueRank, ...], level: int) -> ImbueResolution:
    """Highest imbue rank learnable at `level`."""
    if not ranks:
        return ImbueResolution(None, "has no ranks in configs/spellbook.py")
    rank = imbue_rank_for_level(ranks, level)
    if rank is None:
        first = min(r.level for r in ranks)
        return ImbueResolution(None, f"is first learned at level {first} (character is {level})")
    return ImbueResolution(rank)


def resolve_rank(
    definition: SpellDefinition,
    level: int,
    granted_spells: frozenset[SpellId],
    override: int | None = None,
) -> RankResolution:
    """Highest rank learnable at `level`, or `override` if it is learnable."""
    talent = definition.mechanics.granted_by_talent
    if talent is not None and definition.spell_id not in granted_spells:
        return RankResolution(None, f"requires the {talent} talent")
    if not definition.ranks:
        return RankResolution(None, "has no ranks in configs/spellbook.py")
    if override is not None:
        rank = next((r for r in definition.ranks if r.rank == override), None)
        if rank is None:
            return RankResolution(None, f"has no rank {override} in configs/spellbook.py")
        if rank.level > level:
            return RankResolution(
                None, f"rank {override} is learned at level {rank.level} (character is {level})"
            )
        return RankResolution(rank)
    rank = definition.rank_for_level(level)
    if rank is None:
        first = min(r.level for r in definition.ranks)
        return RankResolution(None, f"is first learned at level {first} (character is {level})")
    return RankResolution(rank)
