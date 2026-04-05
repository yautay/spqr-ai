"""Runtime adapters that convert table models to rule-engine lookups."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.map import TerrainType
from legions_api.core.tables.models import (
    ClashColumnsTableModel,
    MissileTableModel,
    MovementCostsTableModel,
    PursuitOptionTableModel,
    ShockCRTTableModel,
    ShockSuperiorityTableModel,
    StackingMandatoryTableModel,
    StackingVoluntaryTableModel,
    UnitTypeTraitsTableModel,
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


@dataclass(frozen=True, slots=True)
class MissileClassLookup:
    """Runtime lookup fields for one missile class."""

    class_id: str
    strengths_by_range: dict[int, int]


@dataclass(frozen=True, slots=True)
class MissileDRMLookup:
    """Runtime lookup fields for one missile DR modifier."""

    id: str
    drm: int


@dataclass(frozen=True, slots=True)
class ShockCRTCellLookup:
    """Normalized CRT cell values for one roll/column pair."""

    attacker_hits: int
    defender_hits: int


@dataclass(frozen=True, slots=True)
class ShockColumnAdjustmentLookup:
    """Normalized named shock column shift."""

    id: str
    shift: int


@dataclass(frozen=True, slots=True)
class PursuitOptionLookup:
    """Normalized pursuit ratings and DR modifiers."""

    ratings: dict[str, int]
    dr_modifiers: dict[str, int]


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
                raise ValueError(f"movement profile {profile.unit_profile_id!r} uses unknown terrain {terrain_name!r}") from exc
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


def missile_class_lookup(table: MissileTableModel) -> dict[str, MissileClassLookup]:
    """Build range-strength lookup keyed by missile class id."""

    lookup: dict[str, MissileClassLookup] = {}
    for missile_class in table.missile_classes:
        if missile_class.missile_class_id in lookup:
            raise ValueError(f"duplicate missile class id: {missile_class.missile_class_id!r}")

        strengths_by_range: dict[int, int] = {}
        for range_band, strength in missile_class.strength_by_range.items():
            try:
                numeric_range = int(range_band)
            except ValueError as exc:
                raise ValueError(f"missile class {missile_class.missile_class_id!r} uses non-numeric range band {range_band!r}") from exc

            if numeric_range <= 0:
                raise ValueError(f"missile class {missile_class.missile_class_id!r} uses non-positive range band {numeric_range}")

            strengths_by_range[numeric_range] = int(strength)

        lookup[missile_class.missile_class_id] = MissileClassLookup(
            class_id=missile_class.missile_class_id,
            strengths_by_range=strengths_by_range,
        )

    return lookup


def missile_drm_lookup(table: MissileTableModel) -> dict[str, MissileDRMLookup]:
    """Build missile DR-modifier lookup keyed by modifier id."""

    lookup: dict[str, MissileDRMLookup] = {}
    for modifier in table.dr_modifiers:
        if modifier.id in lookup:
            raise ValueError(f"duplicate missile DR modifier id: {modifier.id!r}")

        lookup[modifier.id] = MissileDRMLookup(id=modifier.id, drm=modifier.drm)

    return lookup


def shock_superiority_lookup(table: ShockSuperiorityTableModel) -> dict[tuple[str, str], int]:
    """Build superiority lookup keyed by (attacker_type, defender_type)."""

    lookup: dict[tuple[str, str], int] = {}
    mapping = {"attacker": 1, "defender": -1, "none": 0}
    for row in table.matrix:
        for defender_type, outcome in row.results.items():
            key = (row.attacker_type, defender_type)
            if key in lookup:
                raise ValueError(f"duplicate shock superiority row: attacker={key[0]!r}, defender={key[1]!r}")

            lookup[key] = mapping[outcome]

    return lookup


def clash_column_lookup(table: ClashColumnsTableModel) -> dict[tuple[str, str, str], int]:
    """Build clash-column lookup keyed by (attacker_type, defender_type, angle)."""

    lookup: dict[tuple[str, str, str], int] = {}
    for entry in table.entries:
        key = (entry.attacker_type, entry.defender_type, entry.angle)
        if key in lookup:
            raise ValueError(f"duplicate clash column row: attacker={key[0]!r}, defender={key[1]!r}, angle={key[2]!r}")

        lookup[key] = entry.base_column

    return lookup


def shock_crt_lookup(table: ShockCRTTableModel) -> dict[tuple[int, int], ShockCRTCellLookup]:
    """Build CRT lookup keyed by (column, roll)."""

    lookup: dict[tuple[int, int], ShockCRTCellLookup] = {}
    for raw_column, rows in table.cells.items():
        column = int(raw_column)
        for raw_roll, cell in rows.items():
            roll = int(raw_roll)
            key = (column, roll)
            if key in lookup:
                raise ValueError(f"duplicate shock CRT cell: column={column}, roll={roll}")

            lookup[key] = ShockCRTCellLookup(
                attacker_hits=cell.attacker_hits or 0,
                defender_hits=cell.defender_hits or 0,
            )

    return lookup


def shock_column_adjustment_lookup(table: ShockCRTTableModel) -> dict[str, ShockColumnAdjustmentLookup]:
    """Build lookup for named column adjustments from CRT metadata."""

    lookup: dict[str, ShockColumnAdjustmentLookup] = {}
    for row in table.column_adjustments:
        if row.id in lookup:
            raise ValueError(f"duplicate shock column adjustment id: {row.id!r}")

        shift = row.value if row.direction == "right" else -row.value
        lookup[row.id] = ShockColumnAdjustmentLookup(id=row.id, shift=shift)

    return lookup


def pursuit_option_lookup(table: PursuitOptionTableModel) -> PursuitOptionLookup:
    """Build pursuit option lookup payload from table model."""

    ratings = {key: int(value) for key, value in table.ratings.items()}
    dr_modifiers = {row.id: row.drm for row in table.dr_modifiers}
    return PursuitOptionLookup(ratings=ratings, dr_modifiers=dr_modifiers)


def unit_type_traits_lookup(table: UnitTypeTraitsTableModel) -> dict[str, dict[str, bool]]:
    """Build unit-type trait lookup by canonical unit type id."""

    lookup: dict[str, dict[str, bool]] = {}
    for row in table.unit_types:
        if row.unit_type in lookup:
            raise ValueError(f"duplicate unit_type traits row: {row.unit_type!r}")
        lookup[row.unit_type] = {trait_id: bool(enabled) for trait_id, enabled in row.traits.items()}
    return lookup
