"""Pydantic schemas for external API payloads."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from legions_api.core.model.game_state import TurnPhase
from legions_api.core.model.map import TerrainType
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import MissileSupply, Side


class HexPayload(BaseModel):
    """Serializable axial coordinate payload."""

    q: int
    r: int


class UnitPayload(BaseModel):
    """Serializable unit payload."""

    unit_id: str
    side: Side
    position: HexPayload
    move_allowance: int
    tq: int
    cohesion_hits: int
    is_routed: bool
    exerts_zoc: bool
    move_profile_id: str | None
    stacking_category: str
    missile_class_id: str | None
    missile_supply: MissileSupply
    shock_type: str
    pursuit_capable: bool


class TilePayload(BaseModel):
    """Serializable tile payload."""

    coord: HexPayload
    terrain: TerrainType
    move_cost: int
    passable: bool


class GameStatePayload(BaseModel):
    """Serializable game state payload."""

    ruleset: RulesetMode
    turn_phase: TurnPhase
    tiles: list[TilePayload]
    active_side: Side
    units: list[UnitPayload]


class MoveActionPayload(BaseModel):
    """Move command payload."""

    unit_id: str
    destination: HexPayload


class MissileActionPayload(BaseModel):
    """Missile command payload."""

    firing_unit_id: str
    target_unit_id: str
    modifier_ids: list[str] = Field(default_factory=list)
    fire_mode: Literal["active", "reaction"] = "active"
    reaction_trigger: Literal["entry", "retire", "return"] | None = None


class MissileReloadActionPayload(BaseModel):
    """Missile reload command payload."""

    unit_id: str


class ShockActionPayload(BaseModel):
    """Shock combat command payload."""

    attacker_unit_id: str
    defender_unit_id: str
    angle: Literal["front", "flank", "rear"] = "front"
    modifier_ids: list[str] = Field(default_factory=list)


class NewGamePayload(BaseModel):
    """New game creation options."""

    ruleset: RulesetMode = RulesetMode.ORIGINAL


class SetPhasePayload(BaseModel):
    """Minimal phase transition payload for development flow."""

    phase: TurnPhase


class RulesetsPayload(BaseModel):
    """List of available ruleset identifiers."""

    rulesets: list[RulesetMode]


class GameEventPayload(BaseModel):
    """Realtime event payload emitted over websocket stream."""

    event_id: str
    timestamp: str
    event_type: Literal[
        "game_reset",
        "phase_changed",
        "move_resolved",
        "missile_resolved",
        "reload_resolved",
        "shock_resolved",
        "ai_thinking",
        "ai_move_selected",
    ]
    ok: bool | None = None
    reason: str | None = None
    details: dict[str, str | int | bool | None] = Field(default_factory=dict)


class LegalMoveOptionPayload(BaseModel):
    """One legal destination with deterministic movement path preview."""

    destination: HexPayload
    total_cost: int
    path: list[HexPayload]


class LegalMovesPayload(BaseModel):
    """Legal move options for one unit under current game state."""

    unit_id: str
    options: list[LegalMoveOptionPayload]


class StackingEffectPayload(BaseModel):
    """Stacking side-effect metadata generated during movement."""

    effect_type: str
    interaction: str
    location: HexPayload
    moving_unit_id: str
    stationary_unit_id: str
    moving_unit_cohesion_hits: int
    stationary_unit_cohesion_hits: int
    stationary_unit_tq_check_required: bool
    stationary_unit_tq_check_formula: str | None
    tq_check_drm: int | None


class PendingTQCheckPayload(BaseModel):
    """Deferred TQ check request payload."""

    unit_id: str
    location: HexPayload
    source: str
    required: bool
    formula: str | None
    drm: int | None
    target: int


class TQCheckOutcomePayload(BaseModel):
    """Resolved TQ check with rolled value for UI feedback."""

    unit_id: str
    location: HexPayload
    source: str
    required: bool
    formula: str | None
    drm: int | None
    target: int
    roll: int
    passed: bool
    applied_cohesion_hits: int
    became_routed: bool


class MissileDRMModifierPayload(BaseModel):
    """One missile DR modifier contribution for UI breakdown."""

    id: str
    drm: int


class MissilePreviewPayload(BaseModel):
    """Read-only missile preview details before action execution."""

    firing_unit_id: str
    target_unit_id: str
    fire_mode: Literal["active", "reaction"]
    reaction_trigger: Literal["entry", "retire", "return"] | None
    missile_class_id: str
    range_to_target: int
    table_strength: int
    total_drm: int
    hit_threshold: int
    drm_breakdown: list[MissileDRMModifierPayload]


class MissilePreviewResponsePayload(BaseModel):
    """Missile preview response shape."""

    ok: bool
    reason: str
    preview: MissilePreviewPayload | None


class MissileOutcomePayload(BaseModel):
    """Resolved missile attack details."""

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
    drm_breakdown: list[MissileDRMModifierPayload]


class MissileEventPayload(BaseModel):
    """Domain event emitted by missile and reload resolution."""

    event_type: Literal[
        "missile_fired",
        "reaction_fire",
        "reload_attempt",
        "supply_changed",
        "reaction_window_opened",
        "reaction_window_spent",
    ]
    unit_id: str
    target_unit_id: str | None
    reaction_trigger: Literal["entry", "retire", "return"] | None
    roll: int | None
    target: int | None
    success: bool | None
    supply_before: str | None
    supply_after: str | None


class ShockModifierPayload(BaseModel):
    """One shock column-shift contribution for breakdown UI."""

    id: str
    shift: int


class ShockPreviewPayload(BaseModel):
    """Read-only shock preview details before action execution."""

    attacker_unit_id: str
    defender_unit_id: str
    angle: Literal["front", "flank", "rear"]
    attacker_type: str
    defender_type: str
    base_column: int
    total_shift: int
    final_column: int
    modifier_breakdown: list[ShockModifierPayload]


class ShockPreviewResponsePayload(BaseModel):
    """Shock preview response shape."""

    ok: bool
    reason: str
    preview: ShockPreviewPayload | None


class ShockOutcomePayload(BaseModel):
    """Resolved shock attack details."""

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
    modifier_breakdown: list[ShockModifierPayload]


class MoraleOutcomePayload(BaseModel):
    """Resolved morale outcome emitted by shock sequence."""

    unit_id: str
    source: Literal["shock"]
    target: int
    roll: int
    passed: bool
    became_routed: bool
    retreated: bool
    eliminated: bool


class PursuitOutcomePayload(BaseModel):
    """Pursuit move details after routed enemy retreat/elimination."""

    unit_id: str
    destination: HexPayload


class ActionResponsePayload(BaseModel):
    """Action execution response."""

    ok: bool
    reason: str
    state: GameStatePayload
    effects: list[StackingEffectPayload]
    pending_tq_checks: list[PendingTQCheckPayload]
    tq_check_outcomes: list[TQCheckOutcomePayload]
    missile_outcome: MissileOutcomePayload | None = None
    shock_outcome: ShockOutcomePayload | None = None
    morale_outcomes: list[MoraleOutcomePayload]
    pursuit_outcome: PursuitOutcomePayload | None = None
    events: list[MissileEventPayload]
