"""Movement validation and resolution logic."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import Literal

from legions_api.core.actions import MoveAction
from legions_api.core.model.game_state import GameState, ReactionTrigger, ReactionWindow, TurnPhase
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.leader import Leader
from legions_api.core.model.unit import MissileSupply, Unit
from legions_api.core.random import seeded_d10_roll
from legions_api.core.results import ActionResult, DomainEvent, PendingTQCheck, StackingEffect, TQCheckOutcome
from legions_api.core.rules.pathfinding import MovementPolicy, PathResult, shortest_path
from legions_api.core.rules.zoc import is_in_enemy_zoc
from legions_api.core.tables.adapters import (
    StackingOutcome,
    mandatory_stacking_lookup,
    missile_class_lookup,
    voluntary_stacking_lookup,
)
from legions_api.core.tables.loader import load_table
from legions_api.core.tables.models import MissileTableModel, StackingMandatoryTableModel, StackingVoluntaryTableModel

_ROUTING_CATEGORY_MAP: dict[str, str] = {
    "basic": "routing_basic",
    "scout": "routing_scout",
    "heavy": "routing_heavy",
}


@dataclass(frozen=True, slots=True)
class LegalMoveOption:
    """One legal move destination with deterministic path preview metadata."""

    destination: HexCoord
    total_cost: int
    path: tuple[HexCoord, ...]


@dataclass(frozen=True, slots=True)
class _MoveValidationContext:
    """Precomputed movement validation artifacts reused by resolution and preview APIs."""

    unit: Unit
    use_mandatory_stacking: bool
    stacking_lookup: dict[tuple[str, str], StackingOutcome]
    moving_category: str
    path_result: PathResult


def list_legal_move_options(state: GameState, unit_id: str) -> tuple[LegalMoveOption, ...]:
    """Return legal movement destinations for one unit from current state."""

    unit = state.units.get(unit_id)
    if unit is None or unit.side != state.active_side:
        return ()

    options: list[LegalMoveOption] = []
    sorted_coords = sorted(state.scenario_map.tiles, key=lambda coord: (coord.q, coord.r))
    for destination in sorted_coords:
        if destination == unit.position:
            continue

        context, _ = _validate_move_path(state, MoveAction(unit_id=unit_id, destination=destination))
        if context is None:
            continue

        options.append(
            LegalMoveOption(
                destination=destination,
                total_cost=context.path_result.total_cost,
                path=context.path_result.path,
            )
        )

    return tuple(options)


def resolve_move(state: GameState, action: MoveAction) -> ActionResult:
    """Validate and resolve a move action under current movement and ZOC rules."""

    validation, reason = _validate_move_path(state, action)
    if validation is None:
        return ActionResult(ok=False, reason=reason, state=state)

    try:
        updated_units = dict(state.units)
        movement_effects, moved_unit = _resolve_stacking_side_effects(
            unit=validation.unit,
            destination=action.destination,
            path=validation.path_result.path,
            current_units=updated_units,
            stacking_lookup=validation.stacking_lookup,
            moving_category=validation.moving_category,
            use_mandatory_stacking=validation.use_mandatory_stacking,
        )
        pending_tq_checks = _collect_pending_tq_checks(movement_effects, current_units=updated_units)
        tq_check_outcomes, next_rng_counter = _resolve_pending_tq_checks(
            pending_tq_checks,
            current_units=updated_units,
            rng_seed=state.rng_seed,
            rng_counter=state.rng_counter,
        )
        updated_units[validation.unit.unit_id] = moved_unit.with_position(action.destination)
        reaction_windows = _collect_reaction_windows(
            state=state,
            moving_unit=validation.unit,
            movement_path=validation.path_result.path,
        )
        reaction_events = tuple(
            DomainEvent(
                event_type="reaction_window_opened",
                details={
                    "unit_id": window.firing_unit_id,
                    "target_unit_id": window.target_unit_id,
                    "reaction_trigger": window.reaction_trigger,
                },
            )
            for window in reaction_windows
        )
        next_activation = state.activation.__class__(
            leader_id=state.activation.leader_id,
            orders_remaining=max(0, state.activation.orders_remaining - 1),
            line_commands_remaining=state.activation.line_commands_remaining,
            moved_unit_ids=(*state.activation.moved_unit_ids, validation.unit.unit_id),
            fired_unit_ids=state.activation.fired_unit_ids,
            shocked_unit_ids=state.activation.shocked_unit_ids,
            activated_leader_ids=state.activation.activated_leader_ids,
        )
        updated_state = (
            state.with_units(updated_units)
            .with_rng_counter(next_rng_counter)
            .with_reaction_windows(open_reaction_windows=reaction_windows)
            .with_activation(next_activation)
        )
    except ValueError:
        return ActionResult(ok=False, reason="stacking_category_unmapped", state=state)

    return ActionResult(
        ok=True,
        reason="ok",
        state=updated_state,
        effects=movement_effects,
        pending_tq_checks=pending_tq_checks,
        tq_check_outcomes=tq_check_outcomes,
        events=reaction_events,
    )


def _validate_move_path(
    state: GameState,
    action: MoveAction,
) -> tuple[_MoveValidationContext | None, str]:
    """Validate move command and compute deterministic path metadata when legal."""

    unit = state.units.get(action.unit_id)
    if unit is None:
        return None, "unit_not_found"

    if unit.side != state.active_side:
        return None, "wrong_active_side"

    if state.turn_phase != TurnPhase.ORDERS:
        return None, "wrong_turn_phase"

    active_leader = state.current_active_leader()
    if active_leader is None:
        return None, "no_active_leader"

    if state.activation.orders_remaining <= 0:
        return None, "no_orders_remaining"

    if action.unit_id in state.activation.moved_unit_ids:
        return None, "unit_already_moved_this_activation"

    if not _is_within_command_range(leader=active_leader, unit=unit):
        return None, "unit_out_of_command_range"

    if not state.scenario_map.contains(action.destination):
        return None, "destination_out_of_map"

    if unit.position == action.destination:
        return None, "no_op_move"

    use_mandatory_stacking = unit.is_routed
    try:
        stacking_lookup = _load_stacking_lookup(use_mandatory_stacking)
        moving_category = _moving_stacking_category(unit, use_mandatory_stacking)
    except ValueError:
        return None, "stacking_category_unmapped"

    try:
        destination_units = state.units_at(action.destination)
        if destination_units:
            may_stop_for_all_occupants = all(
                _may_stop_in_hex(
                    stacking_lookup,
                    moving_category=moving_category,
                    stationary_category=_stationary_stacking_category(stationary, use_mandatory_stacking),
                )
                for stationary in destination_units
            )
            if not may_stop_for_all_occupants:
                return None, "destination_occupied"

        if state.ruleset.options.zoc_locks_movement and is_in_enemy_zoc(state, unit.side, unit.position):
            return None, "unit_pinned_by_enemy_zoc"

        def can_traverse_occupied_hex(destination: HexCoord) -> bool:
            occupant_ids = state.occupant_by_hex.get(destination)
            if occupant_ids is None:
                return True

            return all(
                _may_move_through_hex(
                    stacking_lookup,
                    moving_category=moving_category,
                    stationary_category=_stationary_stacking_category(state.units[occupant_id], use_mandatory_stacking),
                )
                for occupant_id in occupant_ids
            )

        path_result = shortest_path(
            state=state,
            side=unit.side,
            unit=unit,
            start=unit.position,
            goal=action.destination,
            policy=MovementPolicy(max_cost=unit.move_allowance, ignore_occupied=False, allow_enter_enemy_zoc=True),
            can_traverse_occupied_hex=can_traverse_occupied_hex,
        )
        if not path_result.found:
            return None, "no_valid_path"
    except ValueError:
        return None, "stacking_category_unmapped"

    return (
        _MoveValidationContext(
            unit=unit,
            use_mandatory_stacking=use_mandatory_stacking,
            stacking_lookup=stacking_lookup,
            moving_category=moving_category,
            path_result=path_result,
        ),
        "ok",
    )


def _load_stacking_lookup(use_mandatory_stacking: bool) -> dict[tuple[str, str], StackingOutcome]:
    """Load normalized lookup for voluntary or mandatory stacking interactions."""

    if use_mandatory_stacking:
        table = load_table("stacking_mandatory")
        if not isinstance(table, StackingMandatoryTableModel):
            raise TypeError("stacking_mandatory table did not resolve to StackingMandatoryTableModel")

        return mandatory_stacking_lookup(table)

    table = load_table("stacking_voluntary")
    if not isinstance(table, StackingVoluntaryTableModel):
        raise TypeError("stacking_voluntary table did not resolve to StackingVoluntaryTableModel")

    return voluntary_stacking_lookup(table)


def _moving_stacking_category(unit: Unit, use_mandatory_stacking: bool) -> str:
    """Resolve moving-unit stacking category for selected chart mode."""

    if use_mandatory_stacking:
        mapped_category = _ROUTING_CATEGORY_MAP.get(unit.stacking_category)
        if mapped_category is None:
            raise ValueError(f"unsupported routed stacking category: {unit.stacking_category!r}")
        return mapped_category

    return unit.stacking_category


def _stationary_stacking_category(unit: Unit, use_mandatory_stacking: bool) -> str:
    """Resolve stationary-unit stacking category for selected chart mode."""

    if use_mandatory_stacking and unit.is_routed:
        mapped_category = _ROUTING_CATEGORY_MAP.get(unit.stacking_category)
        if mapped_category is None:
            raise ValueError(f"unsupported routed stacking category: {unit.stacking_category!r}")
        return mapped_category

    return unit.stacking_category


def _may_move_through_hex(
    lookup: dict[tuple[str, str], StackingOutcome],
    moving_category: str,
    stationary_category: str,
) -> bool:
    """Return whether moving category may pass through stationary category."""

    outcome = lookup.get((moving_category, stationary_category))
    return bool(outcome is not None and outcome.may_move_through)


def _may_stop_in_hex(
    lookup: dict[tuple[str, str], StackingOutcome],
    moving_category: str,
    stationary_category: str,
) -> bool:
    """Return whether moving category may stop in stationary category hex."""

    outcome = lookup.get((moving_category, stationary_category))
    return bool(outcome is not None and outcome.may_stop_in_hex)


def _resolve_stacking_side_effects(
    unit: Unit,
    destination: HexCoord,
    path: tuple[HexCoord, ...],
    current_units: dict[str, Unit],
    stacking_lookup: dict[tuple[str, str], StackingOutcome],
    moving_category: str,
    use_mandatory_stacking: bool,
) -> tuple[tuple[StackingEffect, ...], Unit]:
    """Apply stacking row side effects for occupied hex interactions along movement path."""

    moved_unit = unit
    effects: list[StackingEffect] = []

    for step in path[1:]:
        occupant_ids = [
            unit_id for unit_id, occupant in current_units.items() if occupant.position == step and unit_id != moved_unit.unit_id
        ]
        if not occupant_ids:
            continue

        interaction: Literal["pass_through", "stop_in_hex"]
        if step == destination:
            interaction = "stop_in_hex"
        else:
            interaction = "pass_through"
        for occupant_id in occupant_ids:
            stationary_unit = current_units[occupant_id]
            stationary_category = _stationary_stacking_category(stationary_unit, use_mandatory_stacking)
            outcome = stacking_lookup.get((moving_category, stationary_category))
            if outcome is None:
                continue

            moving_delta = outcome.moving_unit_cohesion_hits or 0
            stationary_delta = outcome.stationary_unit_cohesion_hits or 0

            if moving_delta:
                moved_unit = moved_unit.with_added_cohesion_hits(moving_delta)
            if stationary_delta:
                current_units[occupant_id] = stationary_unit.with_added_cohesion_hits(stationary_delta)

            effects.append(
                StackingEffect(
                    interaction=interaction,
                    location=step,
                    moving_unit_id=moved_unit.unit_id,
                    stationary_unit_id=stationary_unit.unit_id,
                    moving_unit_cohesion_hits=moving_delta,
                    stationary_unit_cohesion_hits=stationary_delta,
                    stationary_unit_tq_check_required=outcome.stationary_unit_tq_check_required,
                    stationary_unit_tq_check_formula=outcome.stationary_unit_tq_check_formula,
                    tq_check_drm=outcome.tq_check_drm,
                )
            )

    return tuple(effects), moved_unit


def _collect_pending_tq_checks(
    effects: tuple[StackingEffect, ...],
    current_units: dict[str, Unit],
) -> tuple[PendingTQCheck, ...]:
    """Collect deferred TQ checks from stacking effects."""

    checks: list[PendingTQCheck] = []
    for effect in effects:
        has_tq_data = (
            effect.stationary_unit_tq_check_required
            or effect.stationary_unit_tq_check_formula is not None
            or effect.tq_check_drm is not None
        )
        if not has_tq_data:
            continue

        stationary_unit = current_units.get(effect.stationary_unit_id)
        if stationary_unit is None:
            continue

        target = _resolve_tq_target(
            base_tq=stationary_unit.tq,
            formula=effect.stationary_unit_tq_check_formula,
            drm=effect.tq_check_drm,
        )

        checks.append(
            PendingTQCheck(
                unit_id=effect.stationary_unit_id,
                location=effect.location,
                source=effect.effect_type,
                required=effect.stationary_unit_tq_check_required,
                formula=effect.stationary_unit_tq_check_formula,
                drm=effect.tq_check_drm,
                target=target,
            )
        )

    return tuple(checks)


def _resolve_tq_target(base_tq: int, formula: str | None, drm: int | None) -> int:
    """Resolve TQ target from base value, formula offset, and DRM."""

    formula_offset = _parse_tq_formula_offset(formula)
    drm_offset = drm or 0
    return base_tq + formula_offset + drm_offset


def _parse_tq_formula_offset(formula: str | None) -> int:
    """Parse compact TQ formula like 'tq', 'tq+2', or 'tq-1'."""

    if formula is None:
        return 0

    raw_formula = formula.strip().lower()
    if raw_formula == "tq":
        return 0
    if raw_formula.startswith("tq+"):
        return int(raw_formula[3:])
    if raw_formula.startswith("tq-"):
        return -int(raw_formula[3:])

    raise ValueError(f"unsupported tq formula: {formula!r}")


def _resolve_pending_tq_checks(
    checks: tuple[PendingTQCheck, ...],
    current_units: dict[str, Unit],
    rng_seed: int,
    rng_counter: int,
) -> tuple[tuple[TQCheckOutcome, ...], int]:
    """Resolve pending TQ checks and apply failure side effects."""

    outcomes: list[TQCheckOutcome] = []
    next_counter = rng_counter
    for check in checks:
        unit = current_units.get(check.unit_id)
        if unit is None:
            continue

        roll = seeded_d10_roll(rng_seed=rng_seed, rng_counter=next_counter)
        next_counter += 1
        passed = roll <= check.target
        applied_cohesion_hits = 0
        became_routed = False
        if not passed:
            applied_cohesion_hits = 1
            failed_unit = unit.with_added_cohesion_hits(applied_cohesion_hits)
            if not failed_unit.is_routed:
                failed_unit = failed_unit.with_routed(True)
                became_routed = True

            current_units[check.unit_id] = failed_unit

        outcomes.append(
            TQCheckOutcome(
                unit_id=check.unit_id,
                location=check.location,
                source=check.source,
                required=check.required,
                formula=check.formula,
                drm=check.drm,
                target=check.target,
                roll=roll,
                passed=passed,
                applied_cohesion_hits=applied_cohesion_hits,
                became_routed=became_routed,
            )
        )

    return tuple(outcomes), next_counter


def _collect_reaction_windows(state: GameState, moving_unit: Unit, movement_path: tuple[HexCoord, ...]) -> tuple[ReactionWindow, ...]:
    """Collect reaction windows opened for enemy missile units by one movement path."""

    if len(movement_path) < 2:
        return ()

    table = load_table("missile_range_results")
    if not isinstance(table, MissileTableModel):
        return ()

    class_lookup = missile_class_lookup(table)
    windows: list[ReactionWindow] = []
    seen: set[ReactionWindow] = set()

    for enemy_unit in state.units.values():
        if enemy_unit.side == moving_unit.side:
            continue
        if enemy_unit.missile_class_id is None:
            continue
        if enemy_unit.missile_supply == MissileSupply.NO:
            continue

        class_row = class_lookup.get(enemy_unit.missile_class_id)
        if class_row is None or not class_row.strengths_by_range:
            continue

        max_range = max(class_row.strengths_by_range)
        for previous, current in pairwise(movement_path):
            trigger = _resolve_reaction_trigger(
                enemy_position=enemy_unit.position,
                previous_position=previous,
                current_position=current,
                max_range=max_range,
            )
            if trigger is None:
                continue

            window = ReactionWindow(
                firing_unit_id=enemy_unit.unit_id,
                target_unit_id=moving_unit.unit_id,
                reaction_trigger=trigger,
            )
            if window in seen:
                continue

            seen.add(window)
            windows.append(window)

    return tuple(windows)


def _resolve_reaction_trigger(
    enemy_position: HexCoord,
    previous_position: HexCoord,
    current_position: HexCoord,
    max_range: int,
) -> ReactionTrigger | None:
    """Resolve reaction trigger opened by one movement step for one enemy missile unit."""

    previous_distance = enemy_position.distance_to(previous_position)
    current_distance = enemy_position.distance_to(current_position)
    was_in_range = previous_distance <= max_range
    is_in_range = current_distance <= max_range

    if not was_in_range and is_in_range:
        return "entry"
    if was_in_range and not is_in_range:
        return "retire"
    if was_in_range and is_in_range and previous_distance != current_distance:
        return "return"

    return None


def _is_within_command_range(leader: Leader, unit: Unit) -> bool:
    """Return whether unit lies within simple leader command radius."""

    return leader.position.distance_to(unit.position) <= leader.command_range
