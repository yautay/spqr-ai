"""Zone of control helpers."""

from __future__ import annotations

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.unit import Side


def enemy_zoc_hexes(state: GameState, side: Side) -> set[HexCoord]:
    """Collect all enemy ZOC coordinates for a given side."""

    zoc: set[HexCoord] = set()
    for unit in state.units.values():
        if unit.side == side or not unit.exerts_zoc:
            continue

        for neighbor in unit.position.neighbors():
            if state.scenario_map.contains(neighbor):
                zoc.add(neighbor)

    return zoc


def is_in_enemy_zoc(state: GameState, side: Side, coord: HexCoord) -> bool:
    """Return True when coordinate is controlled by enemy ZOC."""

    return coord in enemy_zoc_hexes(state, side)
