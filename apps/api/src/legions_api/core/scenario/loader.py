"""Scenario data loader for map and order-of-battle JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, TerrainType, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import MissileSupply, Side, Unit
from legions_api.core.tables.adapters import unit_type_traits_lookup
from legions_api.core.tables.loader import load_ruleset, load_table
from legions_api.core.tables.models import UnitTypeTraitsTableModel

_SCENARIOS_ROOT = Path(__file__).resolve().parents[2] / "data" / "scenarios"
_REQUIRED_SCENARIO_FILES = (
    "map.json",
    "order_of_battle.json",
    "line_command_eligibility.json",
    "victory.json",
    "special_rules.json",
)


def available_scenarios() -> tuple[str, ...]:
    """Return scenario ids with complete required file set."""

    scenario_ids: list[str] = []
    for candidate in sorted(_SCENARIOS_ROOT.iterdir()):
        if not candidate.is_dir() or candidate.name.startswith("_"):
            continue
        if all((candidate / file_name).exists() for file_name in _REQUIRED_SCENARIO_FILES):
            scenario_ids.append(candidate.name)
    return tuple(scenario_ids)


def load_scenario_state(scenario_id: str, mode: RulesetMode = RulesetMode.ORIGINAL) -> GameState:
    """Load one scenario id into immutable runtime game state."""

    scenario_dir = _SCENARIOS_ROOT / scenario_id
    if not scenario_dir.exists() or not scenario_dir.is_dir():
        raise FileNotFoundError(f"unknown scenario_id={scenario_id!r}")

    for required_file in _REQUIRED_SCENARIO_FILES:
        if not (scenario_dir / required_file).exists():
            raise FileNotFoundError(f"scenario {scenario_id!r} misses {required_file!r}")

    raw_map = _load_json(scenario_dir / "map.json")
    raw_oob = _load_json(scenario_dir / "order_of_battle.json")

    ruleset = load_ruleset(mode)
    tiles: list[HexTile] = []
    for raw_tile in _as_list(_as_dict(raw_map["map"])["tiles"]):
        tile_payload = _as_dict(raw_tile)
        terrain = TerrainType(_as_str(tile_payload["terrain"]))
        move_cost = ruleset.movement_cost_for_terrain(terrain)
        tiles.append(
            HexTile(
                coord=HexCoord(q=_as_int(tile_payload["q"]), r=_as_int(tile_payload["r"])),
                terrain=terrain,
                move_cost=move_cost,
                passable=_as_bool(tile_payload.get("passable", True)),
                elevation_level=_as_int(tile_payload.get("elevation", 0)),
            )
        )

    units: dict[str, Unit] = {}
    traits_table = load_table("unit_type_traits")
    if not isinstance(traits_table, UnitTypeTraitsTableModel):
        raise TypeError("unit_type_traits table did not resolve to UnitTypeTraitsTableModel")
    trait_lookup = unit_type_traits_lookup(traits_table)
    for side_payload in _as_list(raw_oob["sides"]):
        side_data = _as_dict(side_payload)
        side = Side(_as_str(side_data["side_id"]))
        for raw_unit in _as_list(side_data.get("units", [])):
            unit_payload = _as_dict(raw_unit)
            unit_id = _as_str(unit_payload["unit_id"])
            missile_supply = MissileSupply.NO if _as_bool(unit_payload.get("depleted", False)) else MissileSupply.NORMAL
            unit_type = _as_str(unit_payload.get("type", "HI"))
            pursuit_capable = _as_bool(unit_payload.get("pursuit_capable", trait_lookup.get(unit_type, {}).get("is_cavalry", False)))
            units[unit_id] = Unit(
                unit_id=unit_id,
                side=side,
                position=HexCoord(
                    q=_as_int(_as_dict(unit_payload["position"])["q"]),
                    r=_as_int(_as_dict(unit_payload["position"])["r"]),
                ),
                move_allowance=_as_int(unit_payload.get("move_allowance", 4)),
                tq=_as_int(unit_payload.get("tq", 7)),
                move_profile_id=None,
                stacking_category=_as_str(unit_payload.get("stacking_category", "basic")),
                missile_class_id=_as_optional_str(unit_payload.get("missile_class")),
                missile_supply=missile_supply,
                shock_type=unit_type,
                pursuit_capable=pursuit_capable,
            )

    return GameState.from_units(
        scenario_map=build_irregular_map(tiles=tiles),
        ruleset=ruleset,
        active_side=Side.RED,
        units=units,
    )


def _load_json(path: Path) -> dict[str, object]:
    """Load one object-shaped JSON file."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"file must contain object payload: {path}")
    return payload


def _as_dict(value: object) -> dict[str, object]:
    """Cast unknown payload to object dictionary."""

    if not isinstance(value, dict):
        raise ValueError("expected object payload")
    return value


def _as_list(value: object) -> list[object]:
    """Cast unknown payload to list."""

    if not isinstance(value, list):
        raise ValueError("expected list payload")
    return value


def _as_str(value: object) -> str:
    """Cast unknown payload value to string."""

    if isinstance(value, str):
        return value
    raise ValueError("expected string payload")


def _as_int(value: object) -> int:
    """Cast unknown payload value to integer."""

    if isinstance(value, bool):
        raise ValueError("expected integer payload")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError("expected integer payload")


def _as_bool(value: object) -> bool:
    """Cast unknown payload value to boolean."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValueError("expected boolean payload")


def _as_optional_str(value: object) -> str | None:
    """Cast optional payload value to optional string."""

    if value is None:
        return None
    return _as_str(value)
