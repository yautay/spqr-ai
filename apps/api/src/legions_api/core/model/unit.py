"""Unit domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from legions_api.core.model.hex import HexCoord


class Side(StrEnum):
    """Battle side identifier."""

    RED = "red"
    BLUE = "blue"


class MissileSupply(StrEnum):
    """Missile ammunition readiness state."""

    NORMAL = "normal"
    LOW = "low"
    NO = "no"


class Facing(IntEnum):
    """Vertex-facing orientation expressed as clockwise hex-vertex angles."""

    DEG_0 = 0
    DEG_60 = 60
    DEG_120 = 120
    DEG_180 = 180
    DEG_240 = 240
    DEG_300 = 300


@dataclass(frozen=True, slots=True)
class Unit:
    """A minimal tactical unit for movement and ZOC simulation."""

    unit_id: str
    side: Side
    position: HexCoord
    position_b: HexCoord | None = None
    facing: Facing = Facing.DEG_0
    unit_class: str | None = None
    size: int = 0
    move_allowance: int = 1
    tq: int = 7
    cohesion_hits: int = 0
    is_routed: bool = False
    is_depleted: bool = False
    exerts_zoc: bool = True
    move_profile_id: str | None = None
    stacking_category: str = "basic"
    missile_class_id: str | None = None
    missile_supply: MissileSupply = MissileSupply.NORMAL
    shock_type: str = "HI"
    pursuit_capable: bool = False

    def with_position(self, position: HexCoord) -> Unit:
        """Return the same unit placed in another coordinate."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=position,
            position_b=self.position_b,
            facing=self.facing,
            unit_class=self.unit_class,
            size=self.size,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits,
            is_routed=self.is_routed,
            is_depleted=self.is_depleted,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
            missile_class_id=self.missile_class_id,
            missile_supply=self.missile_supply,
            shock_type=self.shock_type,
            pursuit_capable=self.pursuit_capable,
        )

    def with_added_cohesion_hits(self, delta: int) -> Unit:
        """Return unit with additional cohesion hits applied."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=self.position,
            position_b=self.position_b,
            facing=self.facing,
            unit_class=self.unit_class,
            size=self.size,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits + delta,
            is_routed=self.is_routed,
            is_depleted=self.is_depleted,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
            missile_class_id=self.missile_class_id,
            missile_supply=self.missile_supply,
            shock_type=self.shock_type,
            pursuit_capable=self.pursuit_capable,
        )

    def with_routed(self, is_routed: bool = True) -> Unit:
        """Return unit with updated routed status."""

        exerts_zoc = self.exerts_zoc and not is_routed

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=self.position,
            position_b=self.position_b,
            facing=self.facing,
            unit_class=self.unit_class,
            size=self.size,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits,
            is_routed=is_routed,
            is_depleted=self.is_depleted,
            exerts_zoc=exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
            missile_class_id=self.missile_class_id,
            missile_supply=self.missile_supply,
            shock_type=self.shock_type,
            pursuit_capable=self.pursuit_capable,
        )

    def with_missile_supply(self, missile_supply: MissileSupply) -> Unit:
        """Return unit with updated missile supply state."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=self.position,
            position_b=self.position_b,
            facing=self.facing,
            unit_class=self.unit_class,
            size=self.size,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits,
            is_routed=self.is_routed,
            is_depleted=self.is_depleted,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
            missile_class_id=self.missile_class_id,
            missile_supply=missile_supply,
            shock_type=self.shock_type,
            pursuit_capable=self.pursuit_capable,
        )

    def with_facing(self, facing: Facing) -> Unit:
        """Return unit with updated orientation."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=self.position,
            position_b=self.position_b,
            facing=facing,
            unit_class=self.unit_class,
            size=self.size,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits,
            is_routed=self.is_routed,
            is_depleted=self.is_depleted,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
            missile_class_id=self.missile_class_id,
            missile_supply=self.missile_supply,
            shock_type=self.shock_type,
            pursuit_capable=self.pursuit_capable,
        )

    def with_depleted(self, is_depleted: bool = True) -> Unit:
        """Return unit with updated depletion state."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=self.position,
            position_b=self.position_b,
            facing=self.facing,
            unit_class=self.unit_class,
            size=self.size,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits,
            is_routed=self.is_routed,
            is_depleted=is_depleted,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
            missile_class_id=self.missile_class_id,
            missile_supply=self.missile_supply,
            shock_type=self.shock_type,
            pursuit_capable=self.pursuit_capable,
        )

    @property
    def occupied_hexes(self) -> tuple[HexCoord, ...]:
        """Return the current footprint occupied by this unit."""

        if self.position_b is None:
            return (self.position,)
        return (self.position, self.position_b)

    @property
    def is_wide(self) -> bool:
        """Return True when the unit occupies two hexes."""

        return self.position_b is not None

    def with_footprint(self, position: HexCoord, position_b: HexCoord | None) -> Unit:
        """Return unit relocated with updated footprint."""

        return Unit(
            unit_id=self.unit_id,
            side=self.side,
            position=position,
            position_b=position_b,
            facing=self.facing,
            unit_class=self.unit_class,
            size=self.size,
            move_allowance=self.move_allowance,
            tq=self.tq,
            cohesion_hits=self.cohesion_hits,
            is_routed=self.is_routed,
            is_depleted=self.is_depleted,
            exerts_zoc=self.exerts_zoc,
            move_profile_id=self.move_profile_id,
            stacking_category=self.stacking_category,
            missile_class_id=self.missile_class_id,
            missile_supply=self.missile_supply,
            shock_type=self.shock_type,
            pursuit_capable=self.pursuit_capable,
        )
