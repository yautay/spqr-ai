"""Pydantic schemas for external API payloads."""

from __future__ import annotations

from pydantic import BaseModel

from legions_api.core.model.map import TerrainType
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import Side


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
    cohesion_hits: int
    exerts_zoc: bool
    move_profile_id: str | None
    stacking_category: str


class TilePayload(BaseModel):
    """Serializable tile payload."""

    coord: HexPayload
    terrain: TerrainType
    move_cost: int
    passable: bool


class GameStatePayload(BaseModel):
    """Serializable game state payload."""

    ruleset: RulesetMode
    tiles: list[TilePayload]
    active_side: Side
    units: list[UnitPayload]


class MoveActionPayload(BaseModel):
    """Move command payload."""

    unit_id: str
    destination: HexPayload


class NewGamePayload(BaseModel):
    """New game creation options."""

    ruleset: RulesetMode = RulesetMode.ORIGINAL


class RulesetsPayload(BaseModel):
    """List of available ruleset identifiers."""

    rulesets: list[RulesetMode]


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


class ActionResponsePayload(BaseModel):
    """Action execution response."""

    ok: bool
    reason: str
    state: GameStatePayload
    effects: list[StackingEffectPayload]
    pending_tq_checks: list[PendingTQCheckPayload]
