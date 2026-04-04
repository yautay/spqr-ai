"""Mapping between domain models and API schemas."""

from __future__ import annotations

from legions_api.api.schemas import (
    ActionResponsePayload,
    GameStatePayload,
    HexPayload,
    PendingTQCheckPayload,
    StackingEffectPayload,
    TilePayload,
    TQCheckOutcomePayload,
    UnitPayload,
)
from legions_api.core.model.game_state import GameState
from legions_api.core.results import ActionResult, PendingTQCheck, StackingEffect, TQCheckOutcome


def to_game_state_payload(state: GameState) -> GameStatePayload:
    """Convert immutable domain state into API payload."""

    sorted_units = sorted(state.units.values(), key=lambda unit: unit.unit_id)
    units = [
        UnitPayload(
            unit_id=unit.unit_id,
            side=unit.side,
            position=HexPayload(q=unit.position.q, r=unit.position.r),
            move_allowance=unit.move_allowance,
            tq=unit.tq,
            cohesion_hits=unit.cohesion_hits,
            is_routed=unit.is_routed,
            exerts_zoc=unit.exerts_zoc,
            move_profile_id=unit.move_profile_id,
            stacking_category=unit.stacking_category,
            missile_class_id=unit.missile_class_id,
        )
        for unit in sorted_units
    ]
    sorted_tiles = sorted(state.scenario_map.tiles.values(), key=lambda tile: (tile.coord.q, tile.coord.r))
    tiles = [
        TilePayload(
            coord=HexPayload(q=tile.coord.q, r=tile.coord.r),
            terrain=tile.terrain,
            move_cost=tile.move_cost,
            passable=tile.passable,
        )
        for tile in sorted_tiles
    ]
    return GameStatePayload(ruleset=state.ruleset.mode, tiles=tiles, active_side=state.active_side, units=units)


def to_action_response_payload(result: ActionResult) -> ActionResponsePayload:
    """Convert core action result to transport payload."""

    return ActionResponsePayload(
        ok=result.ok,
        reason=result.reason,
        state=to_game_state_payload(result.state),
        effects=[_to_stacking_effect_payload(effect) for effect in result.effects],
        pending_tq_checks=[_to_pending_tq_check_payload(check) for check in result.pending_tq_checks],
        tq_check_outcomes=[_to_tq_check_outcome_payload(outcome) for outcome in result.tq_check_outcomes],
    )


def _to_stacking_effect_payload(effect: StackingEffect) -> StackingEffectPayload:
    """Convert stacking effect metadata to API payload."""

    return StackingEffectPayload(
        effect_type=effect.effect_type,
        interaction=effect.interaction,
        location=HexPayload(q=effect.location.q, r=effect.location.r),
        moving_unit_id=effect.moving_unit_id,
        stationary_unit_id=effect.stationary_unit_id,
        moving_unit_cohesion_hits=effect.moving_unit_cohesion_hits,
        stationary_unit_cohesion_hits=effect.stationary_unit_cohesion_hits,
        stationary_unit_tq_check_required=effect.stationary_unit_tq_check_required,
        stationary_unit_tq_check_formula=effect.stationary_unit_tq_check_formula,
        tq_check_drm=effect.tq_check_drm,
    )


def _to_pending_tq_check_payload(check: PendingTQCheck) -> PendingTQCheckPayload:
    """Convert pending TQ check metadata to API payload."""

    return PendingTQCheckPayload(
        unit_id=check.unit_id,
        location=HexPayload(q=check.location.q, r=check.location.r),
        source=check.source,
        required=check.required,
        formula=check.formula,
        drm=check.drm,
        target=check.target,
    )


def _to_tq_check_outcome_payload(outcome: TQCheckOutcome) -> TQCheckOutcomePayload:
    """Convert resolved TQ check outcome to API payload."""

    return TQCheckOutcomePayload(
        unit_id=outcome.unit_id,
        location=HexPayload(q=outcome.location.q, r=outcome.location.r),
        source=outcome.source,
        required=outcome.required,
        formula=outcome.formula,
        drm=outcome.drm,
        target=outcome.target,
        roll=outcome.roll,
        passed=outcome.passed,
        applied_cohesion_hits=outcome.applied_cohesion_hits,
        became_routed=outcome.became_routed,
    )
