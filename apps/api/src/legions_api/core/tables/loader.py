"""Load editable rules tables from JSON files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from legions_api.core.model.map import TerrainType
from legions_api.core.model.ruleset import RulesetDefinition, RulesetMode, RulesetOptions
from legions_api.core.tables.models import (
    LeaderCasualtyTableModel,
    MissileTableModel,
    MovementCostsTableModel,
    ParsedTableModel,
    RallyTableModel,
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
    "rally_table",
    "leader_casualty_table",
]

_SUPPORTED_TABLE_IDS: tuple[TableId, ...] = (
    "movement_costs",
    "stacking_voluntary",
    "stacking_mandatory",
    "missile_range_results",
    "rally_table",
    "leader_casualty_table",
)


@lru_cache(maxsize=4)
def load_ruleset(mode: RulesetMode) -> RulesetDefinition:
    """Load one ruleset definition from editable JSON table."""

    file_path = _RULESET_FILES_DIR / f"{mode.value}.json"
    raw = json.loads(file_path.read_text(encoding="utf-8"))

    raw_mode = RulesetMode(raw["ruleset"])
    terrain_costs = {
        TerrainType(terrain_name): int(cost)
        for terrain_name, cost in raw["movement"]["terrain_costs"].items()
    }
    options = RulesetOptions(zoc_locks_movement=bool(raw["options"]["zoc_locks_movement"]))

    return RulesetDefinition(mode=raw_mode, options=options, terrain_move_costs=terrain_costs)


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
        return StackingVoluntaryTableModel.model_validate(raw)
    if table_id == "stacking_mandatory":
        return StackingMandatoryTableModel.model_validate(raw)
    if table_id == "missile_range_results":
        return MissileTableModel.model_validate(raw)
    if table_id == "rally_table":
        return RallyTableModel.model_validate(raw)
    return LeaderCasualtyTableModel.model_validate(raw)


def load_supported_tables() -> dict[TableId, ParsedTableModel]:
    """Load all currently supported rule tables."""

    return {table_id: load_table(table_id) for table_id in _SUPPORTED_TABLE_IDS}


def available_rulesets() -> tuple[RulesetMode, ...]:
    """Return all supported ruleset modes."""

    return (RulesetMode.ORIGINAL, RulesetMode.SIMPLE)
