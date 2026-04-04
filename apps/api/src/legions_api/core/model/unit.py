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
    tq: int = 7
    cohesion_hits: int = 0
    is_routed: bool = False
    exerts_zoc: bool = True
    move_profile_id: str | None = None
    stacking_category: str = "basic"

    def with_position(self, position: HexCoord) -> Unit:
        """Return the same unit placed in another coordinate."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=position,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits,
            is_routed=self.is_routed,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
        )

    def with_added_cohesion_hits(self, delta: int) -> Unit:
        """Return unit with additional cohesion hits applied."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=self.position,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits + delta,
            is_routed=self.is_routed,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
        )

    def with_routed(self, is_routed: bool = True) -> Unit:
        """Return unit with updated routed status."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=self.position,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits,
            is_routed=is_routed,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
        )
