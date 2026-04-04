"""Tests for map graph and pathfinding behavior."""

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, MapEdge, TerrainType, build_irregular_map, edge_key
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import Side, Unit
from legions_api.core.rules.pathfinding import MovementPolicy, shortest_path
from legions_api.core.tables.loader import load_ruleset


def test_pathfinding_avoids_blocked_edge() -> None:
    """A* should find alternate route when direct edge is blocked."""

    tiles = [
        HexTile(coord=HexCoord(0, 0), terrain=TerrainType.CLEAR),
        HexTile(coord=HexCoord(1, 0), terrain=TerrainType.CLEAR),
        HexTile(coord=HexCoord(0, 1), terrain=TerrainType.CLEAR),
        HexTile(coord=HexCoord(1, 1), terrain=TerrainType.CLEAR),
    ]
    edges = {edge_key(HexCoord(0, 0), HexCoord(1, 0)): MapEdge(blocks_movement=True)}
    scenario_map = build_irregular_map(tiles=tiles, edges=edges)
    units = {"r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=3)}
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = shortest_path(
        state=state,
        side=Side.RED,
        unit=units["r1"],
        start=HexCoord(0, 0),
        goal=HexCoord(1, 0),
        policy=MovementPolicy(max_cost=3),
    )

    assert result.found
    assert result.total_cost == 2
    assert result.path == (HexCoord(0, 0), HexCoord(0, 1), HexCoord(1, 0))


def test_pathfinding_respects_occupied_hexes() -> None:
    """Occupied hexes are avoided unless they are destination."""

    tiles = [
        HexTile(coord=HexCoord(0, 0)),
        HexTile(coord=HexCoord(1, 0)),
        HexTile(coord=HexCoord(0, 1)),
    ]
    scenario_map = build_irregular_map(tiles=tiles)
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=2),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = shortest_path(
        state=state,
        side=Side.RED,
        unit=units["r1"],
        start=HexCoord(0, 0),
        goal=HexCoord(0, 1),
        policy=MovementPolicy(max_cost=2),
    )

    assert result.found
    assert HexCoord(1, 0) not in result.path
