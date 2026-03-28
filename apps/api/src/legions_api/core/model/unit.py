"""Unit domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from legions_api.core.model.hex import HexCoord


class Side(StrEnum):
    """Battle side identifier."""

    RED = "red"
    BLUE = "blue"


@dataclass(frozen=True, slots=True)
class Unit:
    """A minimal tactical unit for movement and ZOC simulation."""

    unit_id: str
    side: Side
    position: HexCoord
    move_allowance: int = 1
    exerts_zoc: bool = True

    def with_position(self, position: HexCoord) -> Unit:
        """Return the same unit placed in another coordinate."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=position,
            move_allowance=self.move_allowance,
            exerts_zoc=self.exerts_zoc,
        )
