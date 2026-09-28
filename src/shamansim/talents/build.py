"""Talent builds parsed from Wowhead calculator URLs."""

from dataclasses import dataclass

from shamansim.core.enums import TalentTree
from shamansim.talents.wowhead import FIRST_TALENT_LEVEL, decode_url


@dataclass(frozen=True, slots=True)
class TalentBuild:
    """A set of talent ranks."""

    url: str
    ranks: dict[str, int]
    points: dict[TalentTree, int]
    talented_rank: int = 0

    @classmethod
    def from_url(cls, url: str) -> "TalentBuild":
        """Parse a Wowhead Forever talent calculator URL."""
        decoded = decode_url(url)
        return cls(url, decoded.ranks, decoded.points, decoded.talented_rank)

    @property
    def total_points(self) -> int:
        """Points spent across all trees."""
        return sum(self.points.values())

    @property
    def required_level(self) -> int:
        """Lowest level with enough talent points."""
        if self.total_points == 0:
            return 1
        return self.total_points + FIRST_TALENT_LEVEL - 1 - self.talented_rank

    @property
    def primary_tree(self) -> TalentTree:
        """Tree with the most points (first in tree order on ties)."""
        return max(TalentTree, key=lambda tree: self.points[tree])

    @property
    def display_name(self) -> str:
        """E.g. 'Fire (0 / 4 / 2)'."""
        counts = " / ".join(str(self.points[tree]) for tree in TalentTree)
        return f"{self.primary_tree.value} ({counts})"

    def rank(self, talent: str) -> int:
        """Rank taken in `talent` (0 if none)."""
        return self.ranks.get(talent, 0)
