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
    ring_hexes: tuple[HexCoord, ...]
    front_hexes: tuple[HexCoord, ...]
    flank_hexes: tuple[HexCoord, ...]
    rear_hexes: tuple[HexCoord, ...]


def unit_geometry(unit: Unit) -> UnitGeometry:
    """Return occupied and surrounding arc hexes for one unit.

    The current runtime still models all units as occupying one anchor hex.
    The helper shape is intentionally footprint-aware so PH can later expand to
    a two-hex geometry without forcing another API-level rewrite.
    """

    if unit.position_b is None:
        occupied_hexes = (unit.position,)
        neighbors = unit.position.neighbors()
        front_directions = _FACING_TO_FRONT_DIRECTIONS[unit.facing]
        rear_directions = tuple((direction + 3) % 6 for direction in front_directions)
        flank_directions = tuple(
            direction
            for direction in range(6)
            if direction not in front_directions and direction not in rear_directions
        )
        ring_hexes = tuple(neighbors)
        front_hexes = tuple(neighbors[direction] for direction in front_directions)
        flank_hexes = tuple(neighbors[direction] for direction in flank_directions)
        rear_hexes = tuple(neighbors[direction] for direction in rear_directions)
    else:
        occupied_hexes = _canonical_occupied_hexes(unit)
        ring_hexes = _wide_ring_hexes(occupied_hexes)
        front_hexes, flank_hexes, rear_hexes = _wide_arc_hexes(unit)

    return UnitGeometry(
        occupied_hexes=occupied_hexes,
        ring_hexes=ring_hexes,
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

    geometry = unit_geometry(defender)
    attack_origins = attacker.occupied_hexes
    if any(origin in geometry.front_hexes for origin in attack_origins):
        return "front"
    if any(origin in geometry.rear_hexes for origin in attack_origins):
        return "rear"
    if any(origin in geometry.flank_hexes for origin in attack_origins):
        return "flank"

    attack_origin = attacker.position
    geometry = unit_geometry(defender)

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


def front_directions(facing: Facing) -> tuple[int, int]:
    """Return the two single-hex front directions for one facing."""

    return _FACING_TO_FRONT_DIRECTIONS[facing]


def opposite_facing(facing: Facing) -> Facing:
    """Return the opposite vertex-facing."""

    return Facing((int(facing) + 180) % 360)


def occupied_hexes(unit: Unit) -> tuple[HexCoord, ...]:
    """Return canonical occupied footprint for one unit."""

    return unit_geometry(unit).occupied_hexes


def is_adjacent_to_unit(attacker: Unit, defender: Unit) -> bool:
    """Return True when any occupied hex of attacker touches defender footprint."""

    defender_hexes = set(defender.occupied_hexes)
    return any(neighbor in defender_hexes for occupied in attacker.occupied_hexes for neighbor in occupied.neighbors())


def contact_hex(attacker: Unit, defender: Unit) -> HexCoord | None:
    """Return one attacker hex adjacent to defender footprint."""

    defender_hexes = set(defender.occupied_hexes)
    for occupied in attacker.occupied_hexes:
        if any(neighbor in defender_hexes for neighbor in occupied.neighbors()):
            return occupied
    return None


def wide_frontage_anchor(unit: Unit) -> HexCoord:
    """Return the front-most anchor hex for wide units and the unit position otherwise."""

    if unit.position_b is None:
        return unit.position

    geometry = unit_geometry(unit)
    for occupied in geometry.occupied_hexes:
        if any(neighbor in geometry.front_hexes for neighbor in occupied.neighbors()):
            return occupied
    return geometry.occupied_hexes[0]


def _canonical_occupied_hexes(unit: Unit) -> tuple[HexCoord, HexCoord]:
    """Return wide footprint in stable order."""

    if unit.position_b is None:
        raise ValueError("wide footprint requires position_b")

    occupied = sorted((unit.position, unit.position_b), key=lambda coord: (coord.q, coord.r))
    return occupied[0], occupied[1]


def _wide_ring_hexes(occupied_hexes: tuple[HexCoord, HexCoord]) -> tuple[HexCoord, ...]:
    """Return the 8-hex outer ring around a two-hex footprint."""

    occupied_set = set(occupied_hexes)
    ring: list[HexCoord] = []
    seen: set[HexCoord] = set()
    for occupied in occupied_hexes:
        for neighbor in occupied.neighbors():
            if neighbor in occupied_set or neighbor in seen:
                continue
            seen.add(neighbor)
            ring.append(neighbor)
    return tuple(sorted(ring, key=lambda coord: (coord.q, coord.r)))


def _wide_arc_hexes(unit: Unit) -> tuple[tuple[HexCoord, ...], tuple[HexCoord, ...], tuple[HexCoord, ...]]:
    """Build wide-unit arcs from the union of each half's local arcs."""

    if unit.position_b is None:
        raise ValueError("wide arcs require a wide unit")

    occupied_set = set(unit.occupied_hexes)
    front: list[HexCoord] = []
    rear: list[HexCoord] = []
    for occupied in unit.occupied_hexes:
        neighbors = occupied.neighbors()
        local_front = front_directions(unit.facing)
        local_rear = tuple((direction + 3) % 6 for direction in local_front)
        for direction in local_front:
            neighbor = neighbors[direction]
            if neighbor not in occupied_set and neighbor not in front:
                front.append(neighbor)
        for direction in local_rear:
            neighbor = neighbors[direction]
            if neighbor not in occupied_set and neighbor not in rear:
                rear.append(neighbor)

    ring = _wide_ring_hexes(_canonical_occupied_hexes(unit))
    flank = [coord for coord in ring if coord not in front and coord not in rear]
    return tuple(front), tuple(flank), tuple(rear)
