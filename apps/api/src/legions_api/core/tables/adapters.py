"""Runtime adapters that convert table models to rule-engine lookups."""

from __future__ import annotations

from legions_api.core.model.map import TerrainType
from legions_api.core.tables.models import MovementCostsTableModel


def movement_costs_by_profile(table: MovementCostsTableModel) -> dict[str, dict[TerrainType, int]]:
    """Build terrain movement lookup keyed by movement profile id."""

    by_profile: dict[str, dict[TerrainType, int]] = {}
    for profile in table.unit_profiles:
        terrain_costs: dict[TerrainType, int] = {}
        for terrain_name, cost_cell in profile.terrain_costs.items():
            if cost_cell.mp is None:
                continue

            try:
                terrain = TerrainType(terrain_name)
            except ValueError as exc:
                raise ValueError(
                    f"movement profile {profile.unit_profile_id!r} uses unknown terrain {terrain_name!r}"
                ) from exc
            terrain_costs[terrain] = int(cost_cell.mp)

        by_profile[profile.unit_profile_id] = terrain_costs

    return by_profile
