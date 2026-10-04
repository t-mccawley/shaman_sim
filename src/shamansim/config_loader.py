"""Loads user configs from a configs directory."""

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Final

from shamansim.core.enums import WeaponImbue
from shamansim.model.character import Character
from shamansim.model.encounter import Encounter
from shamansim.model.meta import MetaConfig
from shamansim.model.rotation import Rotation
from shamansim.model.stat_weights import StatWeightsConfig
from shamansim.spells.definitions import ImbueRank, Spellbook, SpellId, SpellRank
from shamansim.spells.mechanics import build_catalog, build_imbue_catalog
from shamansim.talents.build import TalentBuild

CHARACTER_FILE: Final = "character.py"
ENCOUNTERS_FILE: Final = "encounters.py"
ROTATIONS_FILE: Final = "rotations.py"
TALENTS_FILE: Final = "talents.py"
META_FILE: Final = "meta.py"
SPELLBOOK_FILE: Final = "spellbook.py"
STAT_WEIGHTS_FILE: Final = "stat_weights.py"


@dataclass(frozen=True, slots=True, kw_only=True)
class Configs:
    """All user configuration."""

    characters: list[Character]
    encounters: list[Encounter]
    rotations: list[Rotation]
    talents: list[TalentBuild]
    spellbook: Spellbook
    meta: MetaConfig


def _load_module(path: Path) -> ModuleType:
    if not path.is_file():
        raise FileNotFoundError(f"missing config file: {path}")
    spec = importlib.util.spec_from_file_location(f"shamansim_configs.{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _list_of[T](module: ModuleType, name: str, kind: type[T]) -> list[T]:
    value = getattr(module, name, None)
    if not isinstance(value, list) or not all(isinstance(v, kind) for v in value):
        raise TypeError(f"{module.__name__}.{name} must be a list[{kind.__name__}]")
    return value


def _dict_of_lists[K, V](
    module: ModuleType, name: str, key: type[K], value: type[V]
) -> dict[K, list[V]]:
    data = getattr(module, name, None)
    error = TypeError(
        f"{module.__name__}.{name} must be a dict[{key.__name__}, list[{value.__name__}]]"
    )
    if not isinstance(data, dict):
        raise error
    for k, items in data.items():
        if not isinstance(k, key) or not isinstance(items, list):
            raise error
        if not all(isinstance(item, value) for item in items):
            raise error
    return data


def load_spellbook(directory: Path) -> Spellbook:
    """Spell and imbue ranks from spellbook.py combined with fixed mechanics."""
    module = _load_module(directory / SPELLBOOK_FILE)
    return Spellbook(
        spells=build_catalog(_dict_of_lists(module, "SPELL_RANKS", SpellId, SpellRank)),
        imbues=build_imbue_catalog(_dict_of_lists(module, "IMBUE_RANKS", WeaponImbue, ImbueRank)),
    )


def load_configs(directory: Path) -> Configs:
    """Import every config file in `directory`."""
    meta = getattr(_load_module(directory / META_FILE), "META", None)
    if not isinstance(meta, MetaConfig):
        raise TypeError("meta.META must be a MetaConfig")
    urls = _list_of(_load_module(directory / TALENTS_FILE), "TALENT_URLS", str)
    return Configs(
        characters=_list_of(_load_module(directory / CHARACTER_FILE), "CHARACTERS", Character),
        encounters=_list_of(_load_module(directory / ENCOUNTERS_FILE), "ENCOUNTERS", Encounter),
        rotations=_list_of(_load_module(directory / ROTATIONS_FILE), "ROTATIONS", Rotation),
        talents=[TalentBuild.from_url(url) for url in urls],
        spellbook=load_spellbook(directory),
        meta=meta,
    )


def load_stat_weights(directory: Path) -> StatWeightsConfig:
    """The stat weights selection from stat_weights.py."""
    config = getattr(_load_module(directory / STAT_WEIGHTS_FILE), "STAT_WEIGHTS", None)
    if not isinstance(config, StatWeightsConfig):
        raise TypeError("stat_weights.STAT_WEIGHTS must be a StatWeightsConfig")
    return config
