"""Action types for the core rules engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

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
    modifier_ids: tuple[str, ...] = ()
    fire_mode: Literal["active", "reaction"] = "active"
    reaction_trigger: Literal["entry", "retire", "return"] | None = None


@dataclass(frozen=True, slots=True)
class ReloadMissileAction:
    """Attempt to reload missile supply for one unit."""

    unit_id: str


@dataclass(frozen=True, slots=True)
class ShockAction:
    """Resolve one shock combat attack between adjacent enemy units."""

    attacker_unit_id: str
    defender_unit_id: str
    modifier_ids: tuple[str, ...] = ()
