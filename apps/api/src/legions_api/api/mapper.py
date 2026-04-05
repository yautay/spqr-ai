"""Mapping between domain models and API schemas."""

from __future__ import annotations

from legions_api.api.schemas import (
    ActionResponsePayload,
    GameStatePayload,
    HexPayload,
    LegalMoveOptionPayload,
    LegalMovesPayload,
    MissileDRMModifierPayload,
    MissileEventPayload,
    MissileOutcomePayload,
    MissilePreviewPayload,
    MissilePreviewResponsePayload,
    MoraleOutcomePayload,
    PendingTQCheckPayload,
    PursuitOutcomePayload,
    ShockModifierPayload,
    ShockOutcomePayload,
    ShockPreviewPayload,
    ShockPreviewResponsePayload,
    StackingEffectPayload,
    TilePayload,
    TQCheckOutcomePayload,
    UnitPayload,
)
from legions_api.core.model.game_state import GameState
from legions_api.core.results import (
    ActionResult,
    MissileDRMModifier,
    MissileEvent,
    MissileOutcome,
    MissilePreview,
    MoraleOutcome,
    PendingTQCheck,
    PursuitOutcome,
    ShockModifier,
    ShockOutcome,
    ShockPreview,
    StackingEffect,
    TQCheckOutcome,
)
from legions_api.core.rules.movement import LegalMoveOption


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
            missile_supply=unit.missile_supply,
            shock_type=unit.shock_type,
            pursuit_capable=unit.pursuit_capable,
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
    return GameStatePayload(
        ruleset=state.ruleset.mode,
        turn_phase=state.turn_phase,
        tiles=tiles,
        active_side=state.active_side,
        units=units,
    )


def to_action_response_payload(result: ActionResult) -> ActionResponsePayload:
    """Convert core action result to transport payload."""

    return ActionResponsePayload(
        ok=result.ok,
        reason=result.reason,
        state=to_game_state_payload(result.state),
        effects=[_to_stacking_effect_payload(effect) for effect in result.effects],
        pending_tq_checks=[_to_pending_tq_check_payload(check) for check in result.pending_tq_checks],
        tq_check_outcomes=[_to_tq_check_outcome_payload(outcome) for outcome in result.tq_check_outcomes],
        missile_outcome=_to_missile_outcome_payload(result.missile_outcome),
        shock_outcome=_to_shock_outcome_payload(result.shock_outcome),
        morale_outcomes=[_to_morale_outcome_payload(outcome) for outcome in result.morale_outcomes],
        pursuit_outcome=_to_pursuit_outcome_payload(result.pursuit_outcome),
        events=[_to_missile_event_payload(event) for event in result.events],
    )


def to_legal_moves_payload(unit_id: str, options: tuple[LegalMoveOption, ...]) -> LegalMovesPayload:
    """Convert legal move options to transport payload."""

    return LegalMovesPayload(
        unit_id=unit_id,
        options=[
            LegalMoveOptionPayload(
                destination=HexPayload(q=option.destination.q, r=option.destination.r),
                total_cost=option.total_cost,
                path=[HexPayload(q=coord.q, r=coord.r) for coord in option.path],
            )
            for option in options
        ],
    )


def to_missile_preview_response_payload(preview: MissilePreview | None, reason: str) -> MissilePreviewResponsePayload:
    """Convert missile preview domain output to API response payload."""

    return MissilePreviewResponsePayload(
        ok=preview is not None,
        reason=reason,
        preview=_to_missile_preview_payload(preview),
    )


def to_shock_preview_response_payload(preview: ShockPreview | None, reason: str) -> ShockPreviewResponsePayload:
    """Convert shock preview domain output to API response payload."""

    return ShockPreviewResponsePayload(
        ok=preview is not None,
        reason=reason,
        preview=_to_shock_preview_payload(preview),
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


def _to_missile_outcome_payload(outcome: MissileOutcome | None) -> MissileOutcomePayload | None:
    """Convert missile outcome metadata to API payload."""

    if outcome is None:
        return None

    return MissileOutcomePayload(
        firing_unit_id=outcome.firing_unit_id,
        target_unit_id=outcome.target_unit_id,
        fire_mode=outcome.fire_mode,
        reaction_trigger=outcome.reaction_trigger,
        missile_class_id=outcome.missile_class_id,
        range_to_target=outcome.range_to_target,
        table_strength=outcome.table_strength,
        base_roll=outcome.base_roll,
        total_drm=outcome.total_drm,
        modified_roll=outcome.modified_roll,
        hit=outcome.hit,
        applied_cohesion_hits=outcome.applied_cohesion_hits,
        drm_breakdown=[_to_missile_drm_modifier_payload(modifier) for modifier in outcome.drm_breakdown],
    )


def _to_missile_preview_payload(preview: MissilePreview | None) -> MissilePreviewPayload | None:
    """Convert missile preview metadata to API payload."""

    if preview is None:
        return None

    return MissilePreviewPayload(
        firing_unit_id=preview.firing_unit_id,
        target_unit_id=preview.target_unit_id,
        fire_mode=preview.fire_mode,
        reaction_trigger=preview.reaction_trigger,
        missile_class_id=preview.missile_class_id,
        range_to_target=preview.range_to_target,
        table_strength=preview.table_strength,
        total_drm=preview.total_drm,
        hit_threshold=preview.hit_threshold,
        drm_breakdown=[_to_missile_drm_modifier_payload(modifier) for modifier in preview.drm_breakdown],
    )


def _to_missile_drm_modifier_payload(modifier: MissileDRMModifier) -> MissileDRMModifierPayload:
    """Convert one missile DRM entry to API payload."""

    return MissileDRMModifierPayload(id=modifier.id, drm=modifier.drm)


def _to_missile_event_payload(event: MissileEvent) -> MissileEventPayload:
    """Convert missile domain event to API payload."""

    return MissileEventPayload(
        event_type=event.event_type,
        unit_id=event.unit_id,
        target_unit_id=event.target_unit_id,
        reaction_trigger=event.reaction_trigger,
        roll=event.roll,
        target=event.target,
        success=event.success,
        supply_before=event.supply_before,
        supply_after=event.supply_after,
    )


def _to_shock_outcome_payload(outcome: ShockOutcome | None) -> ShockOutcomePayload | None:
    """Convert shock outcome metadata to API payload."""

    if outcome is None:
        return None

    return ShockOutcomePayload(
        attacker_unit_id=outcome.attacker_unit_id,
        defender_unit_id=outcome.defender_unit_id,
        angle=outcome.angle,
        attacker_type=outcome.attacker_type,
        defender_type=outcome.defender_type,
        base_column=outcome.base_column,
        total_shift=outcome.total_shift,
        final_column=outcome.final_column,
        roll=outcome.roll,
        attacker_hits=outcome.attacker_hits,
        defender_hits=outcome.defender_hits,
        modifier_breakdown=[_to_shock_modifier_payload(entry) for entry in outcome.modifier_breakdown],
    )


def _to_shock_preview_payload(preview: ShockPreview | None) -> ShockPreviewPayload | None:
    """Convert shock preview metadata to API payload."""

    if preview is None:
        return None

    return ShockPreviewPayload(
        attacker_unit_id=preview.attacker_unit_id,
        defender_unit_id=preview.defender_unit_id,
        angle=preview.angle,
        attacker_type=preview.attacker_type,
        defender_type=preview.defender_type,
        base_column=preview.base_column,
        total_shift=preview.total_shift,
        final_column=preview.final_column,
        modifier_breakdown=[_to_shock_modifier_payload(entry) for entry in preview.modifier_breakdown],
    )


def _to_shock_modifier_payload(modifier: ShockModifier) -> ShockModifierPayload:
    """Convert one shock modifier entry to API payload."""

    return ShockModifierPayload(id=modifier.id, shift=modifier.shift)


def _to_morale_outcome_payload(outcome: MoraleOutcome) -> MoraleOutcomePayload:
    """Convert morale outcome metadata to API payload."""

    return MoraleOutcomePayload(
        unit_id=outcome.unit_id,
        source=outcome.source,
        target=outcome.target,
        roll=outcome.roll,
        passed=outcome.passed,
        became_routed=outcome.became_routed,
        retreated=outcome.retreated,
        eliminated=outcome.eliminated,
    )


def _to_pursuit_outcome_payload(outcome: PursuitOutcome | None) -> PursuitOutcomePayload | None:
    """Convert pursuit outcome metadata to API payload."""

    if outcome is None:
        return None

    return PursuitOutcomePayload(
        unit_id=outcome.unit_id,
        destination=HexPayload(q=outcome.destination.q, r=outcome.destination.r),
    )
