"""Movement validation and resolution logic."""

from __future__ import annotations

from typing import Literal

from legions_api.core.actions import MoveAction
from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.unit import Unit
from legions_api.core.results import ActionResult, PendingTQCheck, StackingEffect, TQCheckOutcome
from legions_api.core.rules.pathfinding import MovementPolicy, shortest_path
from legions_api.core.rules.zoc import is_in_enemy_zoc
from legions_api.core.tables.adapters import StackingOutcome, mandatory_stacking_lookup, voluntary_stacking_lookup
from legions_api.core.tables.loader import load_table
from legions_api.core.tables.models import StackingMandatoryTableModel, StackingVoluntaryTableModel

_ROUTING_CATEGORY_MAP: dict[str, str] = {
    "basic": "routing_basic",
    "scout": "routing_scout",
    "heavy": "routing_heavy",
}


def resolve_move(state: GameState, action: MoveAction) -> ActionResult:
    """Validate and resolve a move action under current movement and ZOC rules."""

    unit = state.units.get(action.unit_id)
    if unit is None:
        return ActionResult(ok=False, reason="unit_not_found", state=state)

    if unit.side != state.active_side:
        return ActionResult(ok=False, reason="wrong_active_side", state=state)

    if not state.scenario_map.contains(action.destination):
        return ActionResult(ok=False, reason="destination_out_of_map", state=state)

    if unit.position == action.destination:
        return ActionResult(ok=False, reason="no_op_move", state=state)

    use_mandatory_stacking = unit.is_routed
    try:
        stacking_lookup = _load_stacking_lookup(use_mandatory_stacking)
        moving_category = _moving_stacking_category(unit, use_mandatory_stacking)
    except ValueError:
        return ActionResult(ok=False, reason="stacking_category_unmapped", state=state)

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
                return ActionResult(ok=False, reason="destination_occupied", state=state)

        if state.ruleset.options.zoc_locks_movement and is_in_enemy_zoc(state, unit.side, unit.position):
            return ActionResult(ok=False, reason="unit_pinned_by_enemy_zoc", state=state)

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

        path = shortest_path(
            state=state,
            side=unit.side,
            unit=unit,
            start=unit.position,
            goal=action.destination,
            policy=MovementPolicy(max_cost=unit.move_allowance, ignore_occupied=False, allow_enter_enemy_zoc=True),
            can_traverse_occupied_hex=can_traverse_occupied_hex,
        )
        if not path.found:
            return ActionResult(ok=False, reason="no_valid_path", state=state)

        updated_units = dict(state.units)
        movement_effects, moved_unit = _resolve_stacking_side_effects(
            unit=unit,
            destination=action.destination,
            path=path.path,
            current_units=updated_units,
            stacking_lookup=stacking_lookup,
            moving_category=moving_category,
            use_mandatory_stacking=use_mandatory_stacking,
        )
        pending_tq_checks = _collect_pending_tq_checks(movement_effects, current_units=updated_units)
        tq_check_outcomes, next_rng_counter = _resolve_pending_tq_checks(
            pending_tq_checks,
            current_units=updated_units,
            rng_seed=state.rng_seed,
            rng_counter=state.rng_counter,
        )
        updated_units[unit.unit_id] = moved_unit.with_position(action.destination)
        updated_state = state.with_units(updated_units).with_rng_counter(next_rng_counter)
    except ValueError:
        return ActionResult(ok=False, reason="stacking_category_unmapped", state=state)

    return ActionResult(
        ok=True,
        reason="ok",
        state=updated_state,
        effects=movement_effects,
        pending_tq_checks=pending_tq_checks,
        tq_check_outcomes=tq_check_outcomes,
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
            unit_id
            for unit_id, occupant in current_units.items()
            if occupant.position == step and unit_id != moved_unit.unit_id
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

        roll = _seeded_d10_roll(rng_seed=rng_seed, rng_counter=next_counter)
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


def _seeded_d10_roll(rng_seed: int, rng_counter: int) -> int:
    """Return deterministic seeded d10 roll for current game RNG state."""

    value = (1664525 * rng_seed + 1013904223 * rng_counter) % (2**32)
    return (value % 10) + 1
