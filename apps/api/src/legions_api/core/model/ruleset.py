"""Ruleset profiles and table-driven options."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from legions_api.core.model.map import TerrainType


class RulesetMode(StrEnum):
    """Supported ruleset variants."""

    ORIGINAL = "original"
    SIMPLE = "simple"


@dataclass(frozen=True, slots=True)
class RulesetOptions:
    """Feature flags that change runtime rules behavior."""

    zoc_locks_movement: bool


@dataclass(frozen=True, slots=True)
class RulesetDefinition:
    """Resolved ruleset with options and table values."""

    mode: RulesetMode
    options: RulesetOptions
    terrain_move_costs: dict[TerrainType, int]
