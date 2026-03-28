"""Action types for the core rules engine."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.hex import HexCoord


@dataclass(frozen=True, slots=True)
class MoveAction:
    """Move a unit to an adjacent hex."""

    unit_id: str
    destination: HexCoord
