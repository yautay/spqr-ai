"""Scenario data loader for map and order-of-battle JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.leader import Leader
from legions_api.core.model.map import HexTile, TerrainType, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.scenario import (
    LineAdjacencyRule,
    LineCommandRule,
    LineEligibilityFilter,
    RoutPointRules,
    ScenarioDefinition,
    SpecialRules,
    VictoryRules,
)
from legions_api.core.model.unit import Facing, MissileSupply, Side, Unit
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
    raw_line_rules = _load_json(scenario_dir / "line_command_eligibility.json")
    raw_victory = _load_json(scenario_dir / "victory.json")
    raw_special_rules = _load_json(scenario_dir / "special_rules.json")

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
    leaders: dict[str, Leader] = {}
    traits_table = load_table("unit_type_traits")
    if not isinstance(traits_table, UnitTypeTraitsTableModel):
        raise TypeError("unit_type_traits table did not resolve to UnitTypeTraitsTableModel")
    trait_lookup = unit_type_traits_lookup(traits_table)
    for side_payload in _as_list(raw_oob["sides"]):
        side_data = _as_dict(side_payload)
        side = Side(_as_str(side_data["side_id"]))
        for raw_leader in _as_list(side_data.get("leaders", [])):
            leader_payload = _as_dict(raw_leader)
            leader_id = _as_str(leader_payload["leader_id"])
            leaders[leader_id] = Leader(
                leader_id=leader_id,
                side=side,
                name=_as_str(leader_payload["name"]),
                position=HexCoord(
                    q=_as_int(_as_dict(leader_payload.get("position", {"q": 0, "r": 0}))["q"]),
                    r=_as_int(_as_dict(leader_payload.get("position", {"q": 0, "r": 0}))["r"]),
                ),
                is_overall_commander=_as_bool(leader_payload.get("is_overall_commander", False)),
                initiative=_as_int(leader_payload.get("initiative", 0)),
                command_range=_as_int(leader_payload.get("command_range", 0)),
                line_command=_as_int(leader_payload.get("line_command", 0)),
                strategy=_as_int(leader_payload.get("strategy", 0)),
                charisma=_as_int(leader_payload.get("charisma", 0)),
                elite_commander=_as_bool(leader_payload.get("elite_commander", False)),
                command_restrictions=tuple(_as_str(value) for value in _as_list(leader_payload.get("command_restrictions", []))),
            )
        for raw_unit in _as_list(side_data.get("units", [])):
            unit_payload = _as_dict(raw_unit)
            unit_id = _as_str(unit_payload["unit_id"])
            missile_supply = MissileSupply.NORMAL
            unit_type = _as_str(unit_payload.get("type", "HI"))
            pursuit_capable = _as_bool(unit_payload.get("pursuit_capable", trait_lookup.get(unit_type, {}).get("is_cavalry", False)))
            units[unit_id] = Unit(
                unit_id=unit_id,
                side=side,
                position=HexCoord(
                    q=_as_int(_as_dict(unit_payload["position"])["q"]),
                    r=_as_int(_as_dict(unit_payload["position"])["r"]),
                ),
                facing=Facing(_as_str(unit_payload.get("facing", Facing.NE.value))),
                unit_class=_as_optional_str(unit_payload.get("class")),
                size=_as_int(unit_payload.get("size", 0)),
                move_allowance=_as_int(unit_payload.get("move_allowance", 4)),
                tq=_as_int(unit_payload.get("tq", 7)),
                is_depleted=_as_bool(unit_payload.get("depleted", False)),
                move_profile_id=None,
                stacking_category=_as_str(unit_payload.get("stacking_category", "basic")),
                missile_class_id=_as_optional_str(unit_payload.get("missile_class")),
                missile_supply=missile_supply,
                shock_type=unit_type,
                pursuit_capable=pursuit_capable,
            )

    scenario = ScenarioDefinition(
        line_command_rules=_load_line_command_rules(raw_line_rules),
        special_rules=_load_special_rules(raw_special_rules),
        victory_rules=_load_victory_rules(raw_victory),
    )

    return GameState.from_units(
        scenario_map=build_irregular_map(tiles=tiles),
        scenario=scenario,
        ruleset=ruleset,
        active_side=Side.RED,
        units=units,
        leaders=leaders,
    )


def _load_line_command_rules(payload: dict[str, object]) -> tuple[LineCommandRule, ...]:
    """Load line-command metadata from scenario payload."""

    rules: list[LineCommandRule] = []
    for raw_rule in _as_list(payload.get("line_rules", [])):
        rule_payload = _as_dict(raw_rule)
        filter_payload = _as_dict(rule_payload.get("eligible_unit_filters", {}))
        adjacency_payload = _as_dict(rule_payload.get("adjacency_rule", {}))
        rules.append(
            LineCommandRule(
                line_id=_as_str(rule_payload["line_id"]),
                side=Side(_as_str(rule_payload["side_id"])),
                eligible_unit_filters=LineEligibilityFilter(
                    unit_types=tuple(_as_str(value) for value in _as_list(filter_payload.get("unit_types", []))),
                    unit_classes=tuple(_as_str(value) for value in _as_list(filter_payload.get("unit_classes", []))),
                    allow_velites_skirmish_interruption=_as_bool(
                        filter_payload.get("allow_velites_skirmish_interruption", False)
                    ),
                ),
                adjacency_rule=LineAdjacencyRule(
                    max_gap=_as_int(adjacency_payload.get("max_gap", 0)),
                    allow_gap_through=tuple(_as_str(value) for value in _as_list(adjacency_payload.get("allow_gap_through", []))),
                ),
                requires_same_orientation=_as_bool(rule_payload.get("requires_same_orientation", True)),
                max_lines_per_command=_as_int(rule_payload.get("max_lines_per_command", 1)),
            )
        )
    return tuple(rules)


def _load_special_rules(payload: dict[str, object]) -> SpecialRules:
    """Load scenario special-rule flags."""

    rules_payload = _as_dict(payload.get("rules", {}))
    return SpecialRules(
        carthaginian_command_override=_as_bool(rules_payload.get("carthaginian_command_override", False)),
        triarii_doctrine_active=_as_bool(rules_payload.get("triarii_doctrine_active", False)),
        double_depth_phalanx_allowed=_as_bool(rules_payload.get("double_depth_phalanx_allowed", False)),
        pre_arranged_withdrawal_available=_as_bool(rules_payload.get("pre_arranged_withdrawal_available", False)),
        elephant_command_optional_active=_as_bool(rules_payload.get("elephant_command_optional_active", False)),
        engaged_optional_active=_as_bool(rules_payload.get("engaged_optional_active", False)),
        artillery_active=_as_bool(rules_payload.get("artillery_active", False)),
    )


def _load_victory_rules(payload: dict[str, object]) -> VictoryRules:
    """Load scenario withdrawal and rout-point metadata."""

    retreat_edges_payload = _as_dict(payload.get("retreat_edges", {}))
    withdrawal_levels_payload = _as_dict(payload.get("withdrawal_levels", {}))
    rout_point_payload = _as_dict(payload.get("rout_point_rules", {}))
    leader_rules_payload = _as_dict(rout_point_payload.get("leader_rules", {}))
    return VictoryRules(
        retreat_edges={Side(_as_str(side_id)): _as_str(edge) for side_id, edge in retreat_edges_payload.items()},
        withdrawal_levels={Side(_as_str(side_id)): _as_int(level) for side_id, level in withdrawal_levels_payload.items()},
        rout_point_rules=RoutPointRules(
            default_formula=_as_str(rout_point_payload.get("default", "unit_tq")),
            overrides={
                _as_str(_as_dict(entry).get("unit_id", "")): _as_str(_as_dict(entry).get("formula", "unit_tq"))
                for entry in _as_list(rout_point_payload.get("overrides", []))
                if _as_str(_as_dict(entry).get("unit_id", ""))
            },
            named_multiplier=_as_int(leader_rules_payload.get("named_multiplier", 5)),
            tribune_prefect_replacement=_as_str(leader_rules_payload.get("tribune_prefect_replacement", "initiative")),
        ),
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
