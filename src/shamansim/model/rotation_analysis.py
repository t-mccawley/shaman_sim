"""Static detection of the spells a rotation function uses.

Scans the function's own source for `<x>.fireball` style attributes and
`SpellId.FIREBALL`. A spell whose `.known` is checked anywhere in the function
is treated as handled by the rotation and excluded. Helper functions it calls
are not scanned (the probe run covers those).
"""

import ast
import inspect
import textwrap
from collections.abc import Callable
from typing import Final

from shamansim.spells.definitions import SpellId

KNOWN_ATTRIBUTE: Final = "known"
_BY_PROPERTY: Final = {spell.name.lower(): spell for spell in SpellId}


def _spell_of(node: ast.AST) -> SpellId | None:
    """Spell named by `<x>.fireball` or `SpellId.FIREBALL`, if any."""
    if not isinstance(node, ast.Attribute):
        return None
    if node.attr in _BY_PROPERTY:
        return _BY_PROPERTY[node.attr]
    if (
        isinstance(node.value, ast.Name)
        and node.value.id == SpellId.__name__
        and node.attr in SpellId.__members__
    ):
        return SpellId[node.attr]
    return None


def used_spells(function: Callable[..., object]) -> frozenset[SpellId]:
    """Spells the function references, excluding those it checks with `.known`."""
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
    except (OSError, TypeError, SyntaxError):
        return frozenset()
    nodes = list(ast.walk(tree))
    referenced = {spell for node in nodes if (spell := _spell_of(node)) is not None}
    checked = {
        spell
        for node in nodes
        if isinstance(node, ast.Attribute) and node.attr == KNOWN_ATTRIBUTE
        if (spell := _spell_of(node.value)) is not None
    }
    return frozenset(referenced - checked)
