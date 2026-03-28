"""Movement validation and resolution logic."""

from __future__ import annotations

from legions_api.core.actions import MoveAction
from legions_api.core.model.game_state import GameState
from legions_api.core.results import ActionResult
from legions_api.core.rules.pathfinding import MovementPolicy, shortest_path
from legions_api.core.rules.zoc import is_in_enemy_zoc


def resolve_move(state: GameState, action: MoveAction) -> ActionResult:
    """Validate and resolve a move action under current movement and ZOC rules."""

    unit = state.units.get(action.unit_id)
    if unit is None:
        return ActionResult(ok=False, reason="unit_not_found", state=state)

    if unit.side != state.active_side:
        return ActionResult(ok=False, reason="wrong_active_side", state=state)

    if not state.scenario_map.contains(action.destination):
        return ActionResult(ok=False, reason="destination_out_of_map", state=state)

    if state.unit_at(action.destination) is not None:
        return ActionResult(ok=False, reason="destination_occupied", state=state)

    if unit.position == action.destination:
        return ActionResult(ok=False, reason="no_op_move", state=state)

    if state.ruleset.options.zoc_locks_movement and is_in_enemy_zoc(state, unit.side, unit.position):
        return ActionResult(ok=False, reason="unit_pinned_by_enemy_zoc", state=state)

    path = shortest_path(
        state=state,
        side=unit.side,
        start=unit.position,
        goal=action.destination,
        policy=MovementPolicy(max_cost=unit.move_allowance, ignore_occupied=False, allow_enter_enemy_zoc=True),
    )
    if not path.found:
        return ActionResult(ok=False, reason="no_valid_path", state=state)

    updated_units = dict(state.units)
    updated_units[unit.unit_id] = unit.with_position(action.destination)

    return ActionResult(ok=True, reason="ok", state=state.with_units(updated_units))
