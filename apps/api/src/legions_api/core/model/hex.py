"""Hex coordinate primitives (axial q,r)."""

from __future__ import annotations

from dataclasses import dataclass

_NEIGHBOR_DELTAS: tuple[tuple[int, int], ...] = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


@dataclass(frozen=True, slots=True)
class HexCoord:
    """Axial hex coordinates."""

    q: int
    r: int

    def neighbors(self) -> tuple[HexCoord, ...]:
        """Return the six adjacent axial coordinates."""

        return tuple(HexCoord(self.q + dq, self.r + dr) for dq, dr in _NEIGHBOR_DELTAS)

    def distance_to(self, other: HexCoord) -> int:
        """Cube-distance equivalent computed from axial coordinates."""

        dq = self.q - other.q
        dr = self.r - other.r
        ds = (-self.q - self.r) - (-other.q - other.r)
        return max(abs(dq), abs(dr), abs(ds))

    def direction_to(self, other: HexCoord) -> int | None:
        """Return neighbor direction index to adjacent hex or None otherwise."""

        dq = other.q - self.q
        dr = other.r - self.r
        try:
            return _NEIGHBOR_DELTAS.index((dq, dr))
        except ValueError:
            return None
