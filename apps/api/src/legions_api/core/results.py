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
    target: int


@dataclass(frozen=True, slots=True)
class TQCheckOutcome:
    """Resolved TQ check outcome with deterministic roll metadata."""

    unit_id: str
    location: HexCoord
    source: Literal["stacking"]
    required: bool
    formula: str | None
    drm: int | None
    target: int
    roll: int
    passed: bool
    applied_cohesion_hits: int
    became_routed: bool


@dataclass(frozen=True, slots=True)
class MissileDRMModifier:
    """One missile die-roll modifier contribution."""

    id: str
    drm: int


@dataclass(frozen=True, slots=True)
class MissileOutcome:
    """Resolved missile attack metadata."""

    firing_unit_id: str
    target_unit_id: str
    fire_mode: Literal["active", "reaction"]
    reaction_trigger: Literal["entry", "retire", "return"] | None
    missile_class_id: str
    range_to_target: int
    table_strength: int
    base_roll: int
    total_drm: int
    modified_roll: int
    hit: bool
    applied_cohesion_hits: int
    drm_breakdown: tuple[MissileDRMModifier, ...] = ()


@dataclass(frozen=True, slots=True)
class MissileEvent:
    """Domain event emitted by missile fire/reload resolution."""

    event_type: Literal[
        "missile_fired",
        "reaction_fire",
        "reload_attempt",
        "supply_changed",
        "reaction_window_opened",
        "reaction_window_spent",
    ]
    unit_id: str
    target_unit_id: str | None = None
    reaction_trigger: Literal["entry", "retire", "return"] | None = None
    roll: int | None = None
    target: int | None = None
    success: bool | None = None
    supply_before: str | None = None
    supply_after: str | None = None


@dataclass(frozen=True, slots=True)
class ShockModifier:
    """One shock column-shift contribution."""

    id: str
    shift: int


@dataclass(frozen=True, slots=True)
class ShockOutcome:
    """Resolved shock combat details."""

    attacker_unit_id: str
    defender_unit_id: str
    angle: Literal["front", "flank", "rear"]
    attacker_type: str
    defender_type: str
    base_column: int
    total_shift: int
    final_column: int
    roll: int
    attacker_hits: int
    defender_hits: int
    modifier_breakdown: tuple[ShockModifier, ...] = ()


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Outcome of attempting to resolve an action."""

    ok: bool
    reason: str
    state: GameState
    effects: tuple[StackingEffect, ...] = ()
    pending_tq_checks: tuple[PendingTQCheck, ...] = ()
    tq_check_outcomes: tuple[TQCheckOutcome, ...] = ()
    missile_outcome: MissileOutcome | None = None
    shock_outcome: ShockOutcome | None = None
    events: tuple[MissileEvent, ...] = ()
