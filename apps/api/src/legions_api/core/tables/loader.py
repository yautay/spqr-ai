"""Load editable rules tables from JSON files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from legions_api.core.model.map import TerrainType
from legions_api.core.model.ruleset import RulesetDefinition, RulesetMode, RulesetOptions
from legions_api.core.tables.adapters import movement_costs_by_profile
from legions_api.core.tables.models import (
    ClashColumnsTableModel,
    LeaderCasualtyTableModel,
    MissileTableModel,
    MovementCostsTableModel,
    ParsedTableModel,
    RallyTableModel,
    ShockCRTTableModel,
    ShockSuperiorityTableModel,
    StackingMandatoryTableModel,
    StackingVoluntaryTableModel,
)

_RULESET_FILES_DIR = Path(__file__).resolve().parents[2] / "data" / "rulesets"
_TABLE_FILES_DIR = Path(__file__).resolve().parents[2] / "data" / "tables"

TableId = Literal[
    "movement_costs",
    "stacking_voluntary",
    "stacking_mandatory",
    "missile_range_results",
    "shock_superiority",
    "clash_columns",
    "shock_crt",
    "rally_table",
    "leader_casualty_table",
]

_SUPPORTED_TABLE_IDS: tuple[TableId, ...] = (
    "movement_costs",
    "stacking_voluntary",
    "stacking_mandatory",
    "missile_range_results",
    "shock_superiority",
    "clash_columns",
    "shock_crt",
    "rally_table",
    "leader_casualty_table",
)


@lru_cache(maxsize=4)
def load_ruleset(mode: RulesetMode) -> RulesetDefinition:
    """Load one ruleset definition from editable JSON table."""

    file_path = _RULESET_FILES_DIR / f"{mode.value}.json"
    raw = json.loads(file_path.read_text(encoding="utf-8"))

    raw_mode = RulesetMode(raw["ruleset"])
    movement_profile_id = str(raw["movement"]["default_profile_id"])
    movement_costs_table = load_table("movement_costs")
    if not isinstance(movement_costs_table, MovementCostsTableModel):
        raise TypeError("movement_costs table did not resolve to MovementCostsTableModel")

    costs_by_profile = movement_costs_by_profile(movement_costs_table)
    if movement_profile_id not in costs_by_profile:
        raise ValueError(f"unknown movement profile {movement_profile_id!r} for ruleset {raw_mode.value!r}")

    required_terrains = set(TerrainType)
    for profile_id, terrain_costs in costs_by_profile.items():
        missing_terrains = required_terrains.difference(terrain_costs)
        if missing_terrains:
            missing_names = ", ".join(sorted(str(terrain) for terrain in missing_terrains))
            raise ValueError(f"movement profile {profile_id!r} misses terrain costs: {missing_names}")

    options = RulesetOptions(zoc_locks_movement=bool(raw["options"]["zoc_locks_movement"]))

    return RulesetDefinition(
        mode=raw_mode,
        options=options,
        default_movement_profile_id=movement_profile_id,
        movement_costs_by_profile=costs_by_profile,
    )


def _load_json_file(path: Path) -> dict[str, Any]:
    """Load one JSON file into a dictionary payload."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"table file must contain object payload: {path}")
    return raw


def _resolve_table_path(table_id: TableId) -> Path:
    """Resolve table path preferring finalized JSON over templates."""

    finalized = _TABLE_FILES_DIR / f"{table_id}.json"
    template = _TABLE_FILES_DIR / f"{table_id}.template.json"

    if finalized.exists():
        return finalized
    if template.exists():
        return template
    raise FileNotFoundError(f"no table file found for table_id={table_id}")


@lru_cache(maxsize=32)
def load_table(table_id: TableId) -> ParsedTableModel:
    """Load and validate one rules table by id."""

    path = _resolve_table_path(table_id)
    raw = _load_json_file(path)

    payload_table_id = raw.get("table_id")
    if payload_table_id != table_id:
        raise ValueError(
            f"table_id mismatch in {path}: expected {table_id!r}, got {payload_table_id!r}"
        )

    if table_id == "movement_costs":
        return MovementCostsTableModel.model_validate(raw)
    if table_id == "stacking_voluntary":
        voluntary_table = StackingVoluntaryTableModel.model_validate(raw)
        _validate_stacking_pair_matrix(
            table_id=table_id,
            keys=[(row.moving_category, row.stationary_category) for row in voluntary_table.rows],
        )
        return voluntary_table
    if table_id == "stacking_mandatory":
        mandatory_table = StackingMandatoryTableModel.model_validate(raw)
        _validate_stacking_pair_matrix(
            table_id=table_id,
            keys=[(row.moving_category, row.stationary_category) for row in mandatory_table.rows],
        )
        return mandatory_table
    if table_id == "missile_range_results":
        missile_table = MissileTableModel.model_validate(raw)
        _validate_missile_table(missile_table)
        return missile_table
    if table_id == "shock_superiority":
        return ShockSuperiorityTableModel.model_validate(raw)
    if table_id == "clash_columns":
        return ClashColumnsTableModel.model_validate(raw)
    if table_id == "shock_crt":
        return ShockCRTTableModel.model_validate(raw)
    if table_id == "rally_table":
        return RallyTableModel.model_validate(raw)
    return LeaderCasualtyTableModel.model_validate(raw)


def load_supported_tables() -> dict[TableId, ParsedTableModel]:
    """Load all currently supported rule tables."""

    return {table_id: load_table(table_id) for table_id in _SUPPORTED_TABLE_IDS}


def available_rulesets() -> tuple[RulesetMode, ...]:
    """Return all supported ruleset modes."""

    return (RulesetMode.ORIGINAL, RulesetMode.SIMPLE)


def _validate_stacking_pair_matrix(table_id: str, keys: list[tuple[str, str]]) -> None:
    """Validate uniqueness and matrix completeness for stacking category pairs."""

    moving_categories = sorted({moving for moving, _ in keys})
    stationary_categories = sorted({stationary for _, stationary in keys})

    seen: set[tuple[str, str]] = set()
    duplicates: list[tuple[str, str]] = []
    for key in keys:
        if key in seen:
            duplicates.append(key)
        seen.add(key)

    if duplicates:
        duplicate_names = ", ".join(f"{moving}/{stationary}" for moving, stationary in duplicates)
        raise ValueError(f"{table_id} has duplicate category rows: {duplicate_names}")

    missing: list[tuple[str, str]] = []
    for moving in moving_categories:
        for stationary in stationary_categories:
            pair = (moving, stationary)
            if pair not in seen:
                missing.append(pair)

    if missing:
        missing_names = ", ".join(f"{moving}/{stationary}" for moving, stationary in missing)
        raise ValueError(f"{table_id} misses category pairs: {missing_names}")


def _validate_missile_table(table: MissileTableModel) -> None:
    """Validate uniqueness and contiguous coverage constraints in missile table."""

    class_ids: list[str] = []
    for missile_class in table.missile_classes:
        class_ids.append(missile_class.missile_class_id)

    _validate_unique_names(table_id=table.table_id, label="missile class ids", values=class_ids)

    modifier_ids: list[str] = [modifier.id for modifier in table.dr_modifiers]
    _validate_unique_names(table_id=table.table_id, label="DR modifier ids", values=modifier_ids)


def _validate_unique_names(table_id: str, label: str, values: list[str]) -> None:
    """Validate that string values are unique and non-empty."""

    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{table_id} contains empty value in {label}")
        if normalized in seen:
            duplicates.append(normalized)
        seen.add(normalized)

    if duplicates:
        duplicate_names = ", ".join(duplicates)
        raise ValueError(f"{table_id} has duplicate {label}: {duplicate_names}")
