"""Serialization helpers for immutable game state snapshots."""

from __future__ import annotations

from typing import cast

from legions_api.core.model.game_state import ActivationState, GameState, ReactionTrigger, ReactionWindow, TurnPhase
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.leader import Leader, LeaderStatus
from legions_api.core.model.map import HexTile, MapEdge, TerrainType, build_irregular_map, edge_key
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.scenario import ScenarioDefinition
from legions_api.core.model.unit import Facing, MissileSupply, Side, Unit
from legions_api.core.tables.loader import load_ruleset


def encode_state(state: GameState) -> dict[str, object]:
    """Convert runtime game state into a JSON-serializable dictionary."""

    return {
        "ruleset": state.ruleset.mode.value,
        "active_side": state.active_side.value,
        "rng_seed": state.rng_seed,
        "rng_counter": state.rng_counter,
        "turn_number": state.turn_number,
        "turn_phase": state.turn_phase.value,
        "activation": {
            "leader_id": state.activation.leader_id,
            "orders_remaining": state.activation.orders_remaining,
            "line_commands_remaining": state.activation.line_commands_remaining,
            "moved_unit_ids": list(state.activation.moved_unit_ids),
            "fired_unit_ids": list(state.activation.fired_unit_ids),
            "shocked_unit_ids": list(state.activation.shocked_unit_ids),
            "activated_leader_ids": list(state.activation.activated_leader_ids),
        },
        "map": {
            "tiles": [
                {
                    "q": tile.coord.q,
                    "r": tile.coord.r,
                    "terrain": tile.terrain.value,
                    "move_cost": tile.move_cost,
                    "passable": tile.passable,
                    "elevation_level": tile.elevation_level,
                    "blocks_line_of_sight": tile.blocks_line_of_sight,
                }
                for tile in sorted(state.scenario_map.tiles.values(), key=lambda tile: (tile.coord.q, tile.coord.r))
            ],
            "edges": [
                {
                    "a": {"q": a.q, "r": a.r},
                    "b": {"q": b.q, "r": b.r},
                    "blocks_movement": edge.blocks_movement,
                    "movement_cost_delta": edge.movement_cost_delta,
                    "blocks_line_of_sight": edge.blocks_line_of_sight,
                }
                for (a, b), edge in sorted(
                    state.scenario_map.edges.items(),
                    key=lambda item: (item[0][0].q, item[0][0].r, item[0][1].q, item[0][1].r),
                )
            ],
        },
        "units": [
            {
                "unit_id": unit.unit_id,
                "side": unit.side.value,
                "position": {"q": unit.position.q, "r": unit.position.r},
                "facing": unit.facing.value,
                "unit_class": unit.unit_class,
                "size": unit.size,
                "move_allowance": unit.move_allowance,
                "tq": unit.tq,
                "cohesion_hits": unit.cohesion_hits,
                "is_routed": unit.is_routed,
                "is_depleted": unit.is_depleted,
                "exerts_zoc": unit.exerts_zoc,
                "move_profile_id": unit.move_profile_id,
                "stacking_category": unit.stacking_category,
                "missile_class_id": unit.missile_class_id,
                "missile_supply": unit.missile_supply.value,
                "shock_type": unit.shock_type,
                "pursuit_capable": unit.pursuit_capable,
            }
            for unit in sorted(state.units.values(), key=lambda unit: unit.unit_id)
        ],
        "leaders": [
            {
                "leader_id": leader.leader_id,
                "side": leader.side.value,
                "name": leader.name,
                "position": {"q": leader.position.q, "r": leader.position.r},
                "is_overall_commander": leader.is_overall_commander,
                "initiative": leader.initiative,
                "command_range": leader.command_range,
                "line_command": leader.line_command,
                "strategy": leader.strategy,
                "charisma": leader.charisma,
                "elite_commander": leader.elite_commander,
                "command_restrictions": list(leader.command_restrictions),
                "status": leader.status.value,
            }
            for leader in sorted(state.leaders.values(), key=lambda leader: leader.leader_id)
        ],
        "open_reaction_windows": [_encode_reaction_window(window) for window in state.open_reaction_windows],
        "spent_reaction_windows": [_encode_reaction_window(window) for window in state.spent_reaction_windows],
    }


def decode_state(payload: dict[str, object]) -> GameState:
    """Convert JSON dictionary back into immutable runtime state."""

    ruleset_mode = RulesetMode(str(payload["ruleset"]))
    ruleset = load_ruleset(ruleset_mode)

    raw_map = _as_dict(payload["map"])
    raw_activation = _as_dict(payload.get("activation", {}))
    raw_tiles = _as_list(raw_map["tiles"])
    raw_edges = _as_list(raw_map["edges"])

    tiles = [
        HexTile(
            coord=HexCoord(q=_as_int(_as_dict(tile)["q"]), r=_as_int(_as_dict(tile)["r"])),
            terrain=TerrainType(_as_str(_as_dict(tile)["terrain"])),
            move_cost=_as_int(_as_dict(tile)["move_cost"]),
            passable=_as_bool(_as_dict(tile)["passable"]),
            elevation_level=_as_int(_as_dict(tile).get("elevation_level", 0)),
            blocks_line_of_sight=_as_bool(_as_dict(tile).get("blocks_line_of_sight", False)),
        )
        for tile in raw_tiles
    ]
    edges = {
        edge_key(
            HexCoord(q=_as_int(_as_dict(_as_dict(edge)["a"])["q"]), r=_as_int(_as_dict(_as_dict(edge)["a"])["r"])),
            HexCoord(q=_as_int(_as_dict(_as_dict(edge)["b"])["q"]), r=_as_int(_as_dict(_as_dict(edge)["b"])["r"])),
        ): MapEdge(
            blocks_movement=_as_bool(_as_dict(edge).get("blocks_movement", False)),
            movement_cost_delta=_as_int(_as_dict(edge).get("movement_cost_delta", 0)),
            blocks_line_of_sight=_as_bool(_as_dict(edge).get("blocks_line_of_sight", False)),
        )
        for edge in raw_edges
    }

    units = {
        _as_str(_as_dict(unit)["unit_id"]): Unit(
            unit_id=_as_str(_as_dict(unit)["unit_id"]),
            side=Side(_as_str(_as_dict(unit)["side"])),
            position=HexCoord(
                q=_as_int(_as_dict(_as_dict(unit)["position"])["q"]),
                r=_as_int(_as_dict(_as_dict(unit)["position"])["r"]),
            ),
            facing=Facing(_as_str(_as_dict(unit).get("facing", Facing.NE.value))),
            unit_class=_as_optional_str(_as_dict(unit).get("unit_class")),
            size=_as_int(_as_dict(unit).get("size", 0)),
            move_allowance=_as_int(_as_dict(unit)["move_allowance"]),
            tq=_as_int(_as_dict(unit)["tq"]),
            cohesion_hits=_as_int(_as_dict(unit).get("cohesion_hits", 0)),
            is_routed=_as_bool(_as_dict(unit).get("is_routed", False)),
            is_depleted=_as_bool(_as_dict(unit).get("is_depleted", False)),
            exerts_zoc=_as_bool(_as_dict(unit).get("exerts_zoc", True)),
            move_profile_id=_as_optional_str(_as_dict(unit).get("move_profile_id")),
            stacking_category=_as_str(_as_dict(unit).get("stacking_category", "basic")),
            missile_class_id=_as_optional_str(_as_dict(unit).get("missile_class_id")),
            missile_supply=MissileSupply(_as_str(_as_dict(unit).get("missile_supply", MissileSupply.NORMAL.value))),
            shock_type=_as_str(_as_dict(unit).get("shock_type", "HI")),
            pursuit_capable=_as_bool(_as_dict(unit).get("pursuit_capable", False)),
        )
        for unit in _as_list(payload["units"])
    }
    leaders = {
        _as_str(_as_dict(leader)["leader_id"]): Leader(
            leader_id=_as_str(_as_dict(leader)["leader_id"]),
            side=Side(_as_str(_as_dict(leader)["side"])),
            name=_as_str(_as_dict(leader)["name"]),
            position=HexCoord(
                q=_as_int(_as_dict(_as_dict(leader)["position"])["q"]),
                r=_as_int(_as_dict(_as_dict(leader)["position"])["r"]),
            ),
            is_overall_commander=_as_bool(_as_dict(leader).get("is_overall_commander", False)),
            initiative=_as_int(_as_dict(leader).get("initiative", 0)),
            command_range=_as_int(_as_dict(leader).get("command_range", 0)),
            line_command=_as_int(_as_dict(leader).get("line_command", 0)),
            strategy=_as_int(_as_dict(leader).get("strategy", 0)),
            charisma=_as_int(_as_dict(leader).get("charisma", 0)),
            elite_commander=_as_bool(_as_dict(leader).get("elite_commander", False)),
            command_restrictions=tuple(_as_str(value) for value in _as_list(_as_dict(leader).get("command_restrictions", []))),
            status=LeaderStatus(_as_str(_as_dict(leader).get("status", LeaderStatus.INACTIVE.value))),
        )
        for leader in _as_list(payload.get("leaders", []))
    }

    open_reaction_windows = tuple(_decode_reaction_window(item) for item in _as_list(payload.get("open_reaction_windows", [])))
    spent_reaction_windows = tuple(_decode_reaction_window(item) for item in _as_list(payload.get("spent_reaction_windows", [])))

    return GameState.from_units(
        scenario_map=build_irregular_map(tiles=tiles, edges=edges),
        scenario=ScenarioDefinition(),
        ruleset=ruleset,
        active_side=Side(_as_str(payload["active_side"])),
        units=units,
        leaders=leaders,
        rng_seed=_as_int(payload.get("rng_seed", 1)),
        rng_counter=_as_int(payload.get("rng_counter", 0)),
        turn_number=_as_int(payload.get("turn_number", 1)),
        turn_phase=TurnPhase(_as_str(payload.get("turn_phase", TurnPhase.ORDERS.value))),
        activation=ActivationState(
            leader_id=_as_optional_str(raw_activation.get("leader_id")),
            orders_remaining=_as_int(raw_activation.get("orders_remaining", 0)),
            line_commands_remaining=_as_int(raw_activation.get("line_commands_remaining", 0)),
            moved_unit_ids=tuple(_as_str(value) for value in _as_list(raw_activation.get("moved_unit_ids", []))),
            fired_unit_ids=tuple(_as_str(value) for value in _as_list(raw_activation.get("fired_unit_ids", []))),
            shocked_unit_ids=tuple(_as_str(value) for value in _as_list(raw_activation.get("shocked_unit_ids", []))),
            activated_leader_ids=tuple(_as_str(value) for value in _as_list(raw_activation.get("activated_leader_ids", []))),
        ),
        open_reaction_windows=open_reaction_windows,
        spent_reaction_windows=spent_reaction_windows,
    )


def _encode_reaction_window(window: ReactionWindow) -> dict[str, str]:
    """Serialize one reaction window tuple item."""

    return {
        "firing_unit_id": window.firing_unit_id,
        "target_unit_id": window.target_unit_id,
        "reaction_trigger": window.reaction_trigger,
    }


def _decode_reaction_window(payload: object) -> ReactionWindow:
    """Deserialize one reaction window tuple item."""

    raw = _as_dict(payload)
    return ReactionWindow(
        firing_unit_id=_as_str(raw["firing_unit_id"]),
        target_unit_id=_as_str(raw["target_unit_id"]),
        reaction_trigger=_as_reaction_trigger(raw["reaction_trigger"]),
    )


def _as_dict(value: object) -> dict[str, object]:
    """Cast unknown payload into object dictionary with guard."""

    if not isinstance(value, dict):
        raise ValueError("expected object payload")
    return value


def _as_list(value: object) -> list[object]:
    """Cast unknown payload into list with guard."""

    if not isinstance(value, list):
        raise ValueError("expected list payload")
    return value


def _as_optional_str(value: object) -> str | None:
    """Convert optional payload value to optional string."""

    if value is None:
        return None
    return _as_str(value)


def _as_str(value: object) -> str:
    """Convert payload field to string with guard."""

    if isinstance(value, str):
        return value
    raise ValueError("expected string payload")


def _as_int(value: object) -> int:
    """Convert payload field to integer with guard."""

    if isinstance(value, bool):
        raise ValueError("expected integer payload")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError("expected integer payload")


def _as_bool(value: object) -> bool:
    """Convert payload field to boolean with guard."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValueError("expected boolean payload")


def _as_reaction_trigger(value: object) -> ReactionTrigger:
    """Convert payload field to one supported reaction trigger literal."""

    normalized = _as_str(value)
    if normalized not in {"entry", "retire", "return"}:
        raise ValueError("unknown reaction trigger")
    return cast(ReactionTrigger, normalized)
