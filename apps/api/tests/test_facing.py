"""Facing geometry helper tests."""

from legions_api.core.model.hex import HexCoord
from legions_api.core.model.unit import Facing, Side, Unit
from legions_api.core.rules.facing import flank_hexes, front_hexes, rear_hexes, relative_angle


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
