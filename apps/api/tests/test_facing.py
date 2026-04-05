"""Facing geometry helper tests."""

from legions_api.core.model.hex import HexCoord
from legions_api.core.model.unit import Facing, Side, Unit
from legions_api.core.rules.facing import flank_hexes, front_hexes, is_adjacent_to_unit, rear_hexes, relative_angle


def test_vertex_facing_projects_two_front_hexes() -> None:
    """Facing is anchored on a vertex, so front spans the two adjacent hexsides."""

    unit = Unit(unit_id="u1", side=Side.RED, position=HexCoord(0, 0), facing=Facing.DEG_0)

    assert front_hexes(unit) == (HexCoord(1, -1), HexCoord(0, -1))
    assert flank_hexes(unit) == (HexCoord(1, 0), HexCoord(-1, 0))
    assert rear_hexes(unit) == (HexCoord(-1, 1), HexCoord(0, 1))


def test_relative_angle_uses_defender_vertex_arcs() -> None:
    """Attack angle should derive from defender front/flank/rear arcs."""

    defender = Unit(unit_id="d1", side=Side.BLUE, position=HexCoord(0, 0), facing=Facing.DEG_0)

    assert relative_angle(Unit(unit_id="a1", side=Side.RED, position=HexCoord(1, -1)), defender) == "front"
    assert relative_angle(Unit(unit_id="a2", side=Side.RED, position=HexCoord(1, 0)), defender) == "flank"
    assert relative_angle(Unit(unit_id="a3", side=Side.RED, position=HexCoord(0, 1)), defender) == "rear"


def test_wide_unit_projects_three_front_and_three_rear_hexes() -> None:
    """Wide units use an 8-hex outer ring with 3/2/3 front-flank-rear arcs."""

    unit = Unit(
        unit_id="ph1",
        side=Side.RED,
        position=HexCoord(0, 0),
        position_b=HexCoord(1, 0),
        facing=Facing.DEG_60,
        shock_type="PH",
    )

    assert len(front_hexes(unit)) == 3
    assert len(flank_hexes(unit)) == 2
    assert len(rear_hexes(unit)) == 3


def test_wide_unit_adjacency_checks_any_contact_hex() -> None:
    """Adjacency against wide units should use the whole footprint."""

    defender = Unit(
        unit_id="ph1",
        side=Side.BLUE,
        position=HexCoord(0, 0),
        position_b=HexCoord(1, 0),
        facing=Facing.DEG_60,
        shock_type="PH",
    )
    attacker = Unit(unit_id="a1", side=Side.RED, position=HexCoord(2, 0), facing=Facing.DEG_240)

    assert is_adjacent_to_unit(attacker=attacker, defender=defender)
