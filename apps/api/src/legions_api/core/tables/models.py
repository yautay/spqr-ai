"""Typed models for table-driven original rules data."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BaseTableModel(BaseModel):
    """Common metadata for imported rules tables."""

    table_id: str
    version: str
    notes: str | list[str] | None = None


class TerrainCostCellModel(BaseModel):
    """Movement and cohesion cost in one terrain context."""

    mp: int | None
    cohesion_hits: int | None


class ElevationCostModel(BaseModel):
    """Movement and cohesion cost for elevation transitions."""

    mp: int | None
    cohesion_hits: int | None


class FacingChangeModel(BaseModel):
    """Pivot/facing change costs for one unit profile."""

    mp_per_vertex: int | None
    cohesion_hits_per_vertex_in_rough: int | None


class UnitProfileModel(BaseModel):
    """Movement profile values for one unit type bucket."""

    unit_profile_id: str
    aliases: list[str]
    base_ma: int
    extended_ma: int | None
    terrain_costs: dict[str, TerrainCostCellModel]
    elevation: dict[str, ElevationCostModel]
    facing_change: FacingChangeModel


class MovementCostsTableModel(BaseTableModel):
    """Movement Cost Chart data."""

    table_id: Literal["movement_costs"]
    terrain_types: list[str]
    unit_profiles: list[UnitProfileModel]


class StackingVoluntaryRowModel(BaseModel):
    """One row from voluntary stacking chart."""

    moving_category: str
    stationary_category: str
    may_move_through: bool
    may_stop_in_hex: bool
    moving_unit_cohesion_hits: int | None
    stationary_unit_cohesion_hits: int | None
    tq_check_drm: int | None
    comments: str | None = None


class StackingVoluntaryTableModel(BaseTableModel):
    """Voluntary movement stacking chart data."""

    table_id: Literal["stacking_voluntary"]
    rows: list[StackingVoluntaryRowModel]


class MandatoryTQCheckModel(BaseModel):
    """TQ check condition for mandatory stacking rows."""

    required: bool
    formula: str | None


class StackingMandatoryRowModel(BaseModel):
    """One row from mandatory movement stacking chart."""

    moving_category: str
    stationary_category: str
    may_move_through: bool
    may_stop_in_hex: bool
    moving_unit_cohesion_hits: int | None
    stationary_unit_cohesion_hits: int | None
    stationary_unit_tq_check: MandatoryTQCheckModel
    comments: str | None = None


class StackingMandatoryTableModel(BaseTableModel):
    """Mandatory movement stacking chart data."""

    table_id: Literal["stacking_mandatory"]
    rows: list[StackingMandatoryRowModel]


class MissileClassModel(BaseModel):
    """Missile strength values by range for one missile class."""

    missile_class_id: str
    name: str
    strength_by_range: dict[str, int | None]


class MissileDRModifierModel(BaseModel):
    """Missile die-roll modifier row."""

    id: str
    drm: int | None


class MissileTableModel(BaseTableModel):
    """Missile Range and Results chart data."""

    table_id: Literal["missile_range_results"]
    missile_classes: list[MissileClassModel]
    dr_modifiers: list[MissileDRModifierModel]


class RallyResultModel(BaseModel):
    """Rally table result payload."""

    cohesion_hits_after_rally: int | None


class RallyRowModel(BaseModel):
    """Rally row keyed by die roll."""

    die_roll: int
    result: RallyResultModel


class RallyTableModel(BaseTableModel):
    """Rally table data."""

    table_id: Literal["rally_table"]
    rows: list[RallyRowModel]


class LeaderCasualtyRowModel(BaseModel):
    """Outcome row for leader casualty resolution."""

    die_roll: int
    outcome: str
    effects: list[str]


class LeaderCasualtyTableModel(BaseTableModel):
    """Leader casualty table data."""

    table_id: Literal["leader_casualty_table"]
    rows: list[LeaderCasualtyRowModel]


ParsedTableModel = (
    MovementCostsTableModel
    | StackingVoluntaryTableModel
    | StackingMandatoryTableModel
    | MissileTableModel
    | RallyTableModel
    | LeaderCasualtyTableModel
)
