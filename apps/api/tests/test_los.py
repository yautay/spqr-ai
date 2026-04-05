"""Line-of-sight rule tests."""

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, MapEdge, build_irregular_map, edge_key
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.scenario import ScenarioDefinition
from legions_api.core.model.unit import Side, Unit
from legions_api.core.rules.los import has_line_of_sight
from legions_api.core.tables.loader import load_ruleset


def test_has_line_of_sight_true_when_no_blockers() -> None:
    """LOS should pass on straight clear line."""

    state = _build_state(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(2, 0)),
        ]
    )

    assert has_line_of_sight(state, HexCoord(0, 0), HexCoord(2, 0))


def test_has_line_of_sight_false_when_intermediate_tile_blocks() -> None:
    """LOS should fail when intermediate hex blocks line of sight."""

    state = _build_state(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0), blocks_line_of_sight=True),
            HexTile(coord=HexCoord(2, 0)),
        ]
    )

    assert not has_line_of_sight(state, HexCoord(0, 0), HexCoord(2, 0))


def test_has_line_of_sight_false_when_edge_blocks() -> None:
    """LOS should fail when map edge is flagged as LOS-blocking."""

    a = HexCoord(0, 0)
    b = HexCoord(1, 0)
    c = HexCoord(2, 0)
    state = _build_state(
        tiles=[HexTile(coord=a), HexTile(coord=b), HexTile(coord=c)],
        edges={edge_key(a, b): MapEdge(blocks_line_of_sight=True)},
    )

    assert not has_line_of_sight(state, a, c)


def _build_state(
    tiles: list[HexTile],
    edges: dict[tuple[HexCoord, HexCoord], MapEdge] | None = None,
) -> GameState:
    """Build minimal state used by LOS tests."""

    scenario_map = build_irregular_map(tiles=tiles, edges=edges)
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0)),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(2, 0)),
    }
    return GameState.from_units(
        scenario_map=scenario_map,
        scenario=ScenarioDefinition(),
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )
