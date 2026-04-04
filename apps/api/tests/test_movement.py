"""Movement rule tests."""

from legions_api.core.actions import MoveAction
from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, TerrainType, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import Side, Unit
from legions_api.core.rules.movement import resolve_move
from legions_api.core.tables.loader import load_ruleset


def test_move_fails_when_unit_starts_in_enemy_zoc() -> None:
    """Units cannot move while pinned by adjacent enemy ZOC."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert not result.ok
    assert result.reason == "unit_pinned_by_enemy_zoc"


def test_move_succeeds_when_path_cost_within_allowance() -> None:
    """Movement resolves through pathfinding within move allowance."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(0, 1)),
            HexTile(coord=HexCoord(1, 1)),
        ]
    )
    units = {"r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=2)}
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(1, 1)))

    assert result.ok
    assert result.state.units["r1"].position == HexCoord(1, 1)


def test_simple_ruleset_does_not_lock_movement_in_enemy_zoc() -> None:
    """Simple ruleset allows movement from enemy ZOC for faster play."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.SIMPLE),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert result.ok


def test_move_uses_unit_specific_movement_profile_when_set() -> None:
    """Unit movement profile should override ruleset default terrain costs."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0), terrain=TerrainType.CLEAR),
            HexTile(coord=HexCoord(1, 0), terrain=TerrainType.ROUGH),
        ]
    )
    units = {
        "r1": Unit(
            unit_id="r1",
            side=Side.RED,
            position=HexCoord(0, 0),
            move_allowance=1,
            move_profile_id="simple_standard",
        )
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(1, 0)))

    assert result.ok
