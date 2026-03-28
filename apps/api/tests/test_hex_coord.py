"""Tests for axial coordinate helpers."""

from legions_api.core.model.hex import HexCoord


def test_neighbors_returns_six_unique_hexes() -> None:
    """Axial coordinate should always return six unique adjacent hexes."""

    center = HexCoord(0, 0)

    neighbors = center.neighbors()

    assert len(neighbors) == 6
    assert len(set(neighbors)) == 6


def test_distance_is_symmetric_and_matches_hex_steps() -> None:
    """Distance function matches cube-equivalent hex distance."""

    start = HexCoord(0, 0)
    target = HexCoord(2, -1)

    assert start.distance_to(target) == 2
    assert target.distance_to(start) == 2
