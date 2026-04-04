"""Action types for the core rules engine."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.hex import HexCoord


@dataclass(frozen=True, slots=True)
class MoveAction:
    """Move a unit to an adjacent hex."""

    unit_id: str
    destination: HexCoord


@dataclass(frozen=True, slots=True)
class MissileAction:
    """Resolve one direct missile attack against a target unit."""

    firing_unit_id: str
    target_unit_id: str
