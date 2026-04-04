"""Line-of-sight helpers for missile resolution."""

from __future__ import annotations

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import edge_key


def has_line_of_sight(state: GameState, origin: HexCoord, target: HexCoord) -> bool:
    """Return whether LOS is clear between two coordinates."""

    line = _hex_line(origin, target)
    if not line:
        return False

    previous = line[0]
    for current in line[1:]:
        edge = state.scenario_map.edges.get(edge_key(previous, current))
        if edge is not None and edge.blocks_line_of_sight:
            return False

        if current != target:
            tile = state.scenario_map.tile_at(current)
            if tile is None or tile.blocks_line_of_sight:
                return False

        previous = current

    return True


def _hex_line(start: HexCoord, end: HexCoord) -> tuple[HexCoord, ...]:
    """Return rounded line coordinates from start to end (inclusive)."""

    distance = start.distance_to(end)
    if distance == 0:
        return (start,)

    a = _to_cube(start)
    b = _to_cube(end)
    step = 1.0 / distance

    points: list[HexCoord] = []
    for index in range(distance + 1):
        t = step * index
        points.append(_cube_round(_cube_lerp(a, b, t)))

    return tuple(points)


def _to_cube(coord: HexCoord) -> tuple[float, float, float]:
    """Convert axial coordinate to cube coordinates."""

    x = float(coord.q)
    z = float(coord.r)
    y = -x - z
    return (x, y, z)


def _cube_lerp(a: tuple[float, float, float], b: tuple[float, float, float], t: float) -> tuple[float, float, float]:
    """Interpolate cube coordinates using scalar t in [0, 1]."""

    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _cube_round(cube: tuple[float, float, float]) -> HexCoord:
    """Round cube coordinate to nearest axial hex."""

    x, y, z = cube
    rx = round(x)
    ry = round(y)
    rz = round(z)

    x_diff = abs(rx - x)
    y_diff = abs(ry - y)
    z_diff = abs(rz - z)

    if x_diff > y_diff and x_diff > z_diff:
        rx = -ry - rz
    elif y_diff > z_diff:
        ry = -rx - rz
    else:
        rz = -rx - ry

    _ = ry
    return HexCoord(q=int(rx), r=int(rz))
