"""Action validation and resolution result models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord


@dataclass(frozen=True, slots=True)
class StackingEffect:
    """Stacking side-effect metadata emitted during movement resolution."""

    interaction: Literal["pass_through", "stop_in_hex"]
    location: HexCoord
    moving_unit_id: str
    stationary_unit_id: str
    moving_unit_cohesion_hits: int
    stationary_unit_cohesion_hits: int
    stationary_unit_tq_check_required: bool
    stationary_unit_tq_check_formula: str | None
    tq_check_drm: int | None
    effect_type: Literal["stacking"] = "stacking"


@dataclass(frozen=True, slots=True)
class PendingTQCheck:
    """Deferred TQ check request produced by action side effects."""

    unit_id: str
    location: HexCoord
    source: Literal["stacking"]
    required: bool
    formula: str | None
    drm: int | None


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Outcome of attempting to resolve an action."""

    ok: bool
    reason: str
    state: GameState
    effects: tuple[StackingEffect, ...] = ()
    pending_tq_checks: tuple[PendingTQCheck, ...] = ()
