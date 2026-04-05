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
    default_movement_profile_id: str
    movement_costs_by_profile: dict[str, dict[TerrainType, int]]

    def movement_cost_for_terrain(self, terrain: TerrainType, profile_id: str | None = None) -> int:
        """Return terrain movement cost from selected profile or ruleset default."""

        selected_profile_id = profile_id or self.default_movement_profile_id
        profile_costs = self.movement_costs_by_profile.get(selected_profile_id)
        if profile_costs is None:
            raise ValueError(f"unknown movement profile: {selected_profile_id}")

        terrain_cost = profile_costs.get(terrain)
        if terrain_cost is None:
            raise ValueError(f"movement profile {selected_profile_id!r} does not define terrain {terrain.value!r}")

        return terrain_cost
