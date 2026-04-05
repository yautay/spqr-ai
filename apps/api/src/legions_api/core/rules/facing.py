"""Facing and footprint helpers for front/flank/rear-sensitive rules."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.hex import HexCoord
from legions_api.core.model.unit import Facing, Unit

NeighborDirection = int

_FACING_TO_FRONT_DIRECTIONS: dict[Facing, tuple[NeighborDirection, ...]] = {
    Facing.DEG_0: (1, 2),
    Facing.DEG_60: (0, 1),
    Facing.DEG_120: (0, 5),
    Facing.DEG_180: (5, 4),
    Facing.DEG_240: (3, 4),
    Facing.DEG_300: (2, 3),
}


@dataclass(frozen=True, slots=True)
class UnitGeometry:
    """Derived local geometry around one unit footprint."""

    occupied_hexes: tuple[HexCoord, ...]
    front_hexes: tuple[HexCoord, ...]
    flank_hexes: tuple[HexCoord, ...]
    rear_hexes: tuple[HexCoord, ...]


def unit_geometry(unit: Unit) -> UnitGeometry:
    """Return occupied and surrounding arc hexes for one unit.

    The current runtime still models all units as occupying one anchor hex.
    The helper shape is intentionally footprint-aware so PH can later expand to
    a two-hex geometry without forcing another API-level rewrite.
    """

    occupied_hexes = (unit.position,)
    neighbors = unit.position.neighbors()
    front_directions = _FACING_TO_FRONT_DIRECTIONS[unit.facing]
    rear_directions = tuple((direction + 3) % 6 for direction in front_directions)
    flank_directions = tuple(
        direction
        for direction in range(6)
        if direction not in front_directions and direction not in rear_directions
    )

    front_hexes = tuple(neighbors[direction] for direction in front_directions)
    flank_hexes = tuple(neighbors[direction] for direction in flank_directions)
    rear_hexes = tuple(neighbors[direction] for direction in rear_directions)
    return UnitGeometry(
        occupied_hexes=occupied_hexes,
        front_hexes=front_hexes,
        flank_hexes=flank_hexes,
        rear_hexes=rear_hexes,
    )


def front_hexes(unit: Unit) -> tuple[HexCoord, ...]:
    """Return frontal adjacent hexes covered by the unit ZOC."""

    return unit_geometry(unit).front_hexes


def flank_hexes(unit: Unit) -> tuple[HexCoord, ...]:
    """Return flank-adjacent hexes around the unit."""

    return unit_geometry(unit).flank_hexes


def rear_hexes(unit: Unit) -> tuple[HexCoord, ...]:
    """Return rear-adjacent hexes around the unit."""

    return unit_geometry(unit).rear_hexes


def relative_angle(attacker: Unit, defender: Unit) -> str:
    """Return front/flank/rear angle against defender based on defender facing."""

    attack_origin = attacker.position
    geometry = unit_geometry(defender)
    if attack_origin in geometry.front_hexes:
        return "front"
    if attack_origin in geometry.rear_hexes:
        return "rear"
    if attack_origin in geometry.flank_hexes:
        return "flank"

    direction = defender.position.direction_to(attacker.position)
    if direction is None:
        return "front"

    front_directions = _FACING_TO_FRONT_DIRECTIONS[defender.facing]
    rear_directions = tuple((entry + 3) % 6 for entry in front_directions)
    if direction in front_directions:
        return "front"
    if direction in rear_directions:
        return "rear"
    return "flank"


def facing_from_direction(direction_index: int) -> Facing:
    """Return the vertex-facing whose front arc contains the direction index."""

    normalized = direction_index % 6
    for facing, directions in _FACING_TO_FRONT_DIRECTIONS.items():
        if normalized in directions:
            return facing
    raise ValueError(f"unsupported direction index: {direction_index}")
