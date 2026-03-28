"""Create baseline game states for development."""

from __future__ import annotations

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, TerrainType, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import Side, Unit
from legions_api.core.tables.loader import load_ruleset


def create_demo_state(mode: RulesetMode = RulesetMode.ORIGINAL) -> GameState:
    """Return a deterministic demo state for API and UI integration."""

    ruleset = load_ruleset(mode)

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(
                coord=HexCoord(0, 0),
                terrain=TerrainType.CLEAR,
                move_cost=ruleset.terrain_move_costs[TerrainType.CLEAR],
            ),
            HexTile(
                coord=HexCoord(1, 0),
                terrain=TerrainType.CLEAR,
                move_cost=ruleset.terrain_move_costs[TerrainType.CLEAR],
            ),
            HexTile(
                coord=HexCoord(1, -1),
                terrain=TerrainType.ROUGH,
                move_cost=ruleset.terrain_move_costs[TerrainType.ROUGH],
            ),
            HexTile(
                coord=HexCoord(0, -1),
                terrain=TerrainType.CLEAR,
                move_cost=ruleset.terrain_move_costs[TerrainType.CLEAR],
            ),
            HexTile(
                coord=HexCoord(-1, 0),
                terrain=TerrainType.WOODS,
                move_cost=ruleset.terrain_move_costs[TerrainType.WOODS],
            ),
            HexTile(
                coord=HexCoord(-1, 1),
                terrain=TerrainType.CLEAR,
                move_cost=ruleset.terrain_move_costs[TerrainType.CLEAR],
            ),
            HexTile(
                coord=HexCoord(0, 1),
                terrain=TerrainType.CLEAR,
                move_cost=ruleset.terrain_move_costs[TerrainType.CLEAR],
            ),
            HexTile(
                coord=HexCoord(2, -1),
                terrain=TerrainType.CLEAR,
                move_cost=ruleset.terrain_move_costs[TerrainType.CLEAR],
            ),
            HexTile(
                coord=HexCoord(2, 0),
                terrain=TerrainType.CLEAR,
                move_cost=ruleset.terrain_move_costs[TerrainType.CLEAR],
            ),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0)),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(2, -1)),
    }
    return GameState.from_units(scenario_map=scenario_map, ruleset=ruleset, active_side=Side.RED, units=units)
