"""Runtime adapters that convert table models to rule-engine lookups."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.map import TerrainType
from legions_api.core.tables.models import (
    MovementCostsTableModel,
    StackingMandatoryTableModel,
    StackingVoluntaryTableModel,
)


@dataclass(frozen=True, slots=True)
class StackingOutcome:
    """Normalized runtime outcome for one stacking interaction row."""

    may_move_through: bool
    may_stop_in_hex: bool
    moving_unit_cohesion_hits: int | None
    stationary_unit_cohesion_hits: int | None
    stationary_unit_tq_check_required: bool
    stationary_unit_tq_check_formula: str | None
    tq_check_drm: int | None


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


def voluntary_stacking_lookup(table: StackingVoluntaryTableModel) -> dict[tuple[str, str], StackingOutcome]:
    """Build lookup keyed by (moving_category, stationary_category)."""

    lookup: dict[tuple[str, str], StackingOutcome] = {}
    for row in table.rows:
        key = (row.moving_category, row.stationary_category)
        if key in lookup:
            raise ValueError(f"duplicate voluntary stacking row: moving={key[0]!r}, stationary={key[1]!r}")

        lookup[key] = StackingOutcome(
            may_move_through=row.may_move_through,
            may_stop_in_hex=row.may_stop_in_hex,
            moving_unit_cohesion_hits=row.moving_unit_cohesion_hits,
            stationary_unit_cohesion_hits=row.stationary_unit_cohesion_hits,
            stationary_unit_tq_check_required=False,
            stationary_unit_tq_check_formula=None,
            tq_check_drm=row.tq_check_drm,
        )

    return lookup


def mandatory_stacking_lookup(table: StackingMandatoryTableModel) -> dict[tuple[str, str], StackingOutcome]:
    """Build lookup keyed by (moving_category, stationary_category)."""

    lookup: dict[tuple[str, str], StackingOutcome] = {}
    for row in table.rows:
        key = (row.moving_category, row.stationary_category)
        if key in lookup:
            raise ValueError(f"duplicate mandatory stacking row: moving={key[0]!r}, stationary={key[1]!r}")

        lookup[key] = StackingOutcome(
            may_move_through=row.may_move_through,
            may_stop_in_hex=row.may_stop_in_hex,
            moving_unit_cohesion_hits=row.moving_unit_cohesion_hits,
            stationary_unit_cohesion_hits=row.stationary_unit_cohesion_hits,
            stationary_unit_tq_check_required=row.stationary_unit_tq_check.required,
            stationary_unit_tq_check_formula=row.stationary_unit_tq_check.formula,
            tq_check_drm=None,
        )

    return lookup
