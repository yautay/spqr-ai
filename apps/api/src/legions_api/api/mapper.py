"""Mapping between domain models and API schemas."""

from __future__ import annotations

from legions_api.api.schemas import GameStatePayload, HexPayload, TilePayload, UnitPayload
from legions_api.core.model.game_state import GameState


def to_game_state_payload(state: GameState) -> GameStatePayload:
    """Convert immutable domain state into API payload."""

    sorted_units = sorted(state.units.values(), key=lambda unit: unit.unit_id)
    units = [
        UnitPayload(
            unit_id=unit.unit_id,
            side=unit.side,
            position=HexPayload(q=unit.position.q, r=unit.position.r),
            move_allowance=unit.move_allowance,
            exerts_zoc=unit.exerts_zoc,
            move_profile_id=unit.move_profile_id,
        )
        for unit in sorted_units
    ]
    sorted_tiles = sorted(state.scenario_map.tiles.values(), key=lambda tile: (tile.coord.q, tile.coord.r))
    tiles = [
        TilePayload(
            coord=HexPayload(q=tile.coord.q, r=tile.coord.r),
            terrain=tile.terrain,
            move_cost=tile.move_cost,
            passable=tile.passable,
        )
        for tile in sorted_tiles
    ]
    return GameStatePayload(ruleset=state.ruleset.mode, tiles=tiles, active_side=state.active_side, units=units)
