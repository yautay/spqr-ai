"""Movement validation and resolution logic."""

from __future__ import annotations

from legions_api.core.actions import MoveAction
from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.results import ActionResult
from legions_api.core.rules.pathfinding import MovementPolicy, shortest_path
from legions_api.core.rules.zoc import is_in_enemy_zoc
from legions_api.core.tables.adapters import StackingOutcome, voluntary_stacking_lookup
from legions_api.core.tables.loader import load_table
from legions_api.core.tables.models import StackingVoluntaryTableModel


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

    stacking_lookup = _load_voluntary_stacking_lookup()

    destination_unit = state.unit_at(action.destination)
    if destination_unit is not None:
        destination_outcome = stacking_lookup.get((unit.stacking_category, destination_unit.stacking_category))
        if destination_outcome is not None and destination_outcome.may_stop_in_hex:
            return ActionResult(ok=False, reason="stacking_stop_not_supported", state=state)
        return ActionResult(ok=False, reason="destination_occupied", state=state)

    if state.ruleset.options.zoc_locks_movement and is_in_enemy_zoc(state, unit.side, unit.position):
        return ActionResult(ok=False, reason="unit_pinned_by_enemy_zoc", state=state)

    def can_traverse_occupied_hex(destination: HexCoord) -> bool:
        occupant_id = state.occupant_by_hex.get(destination)
        if occupant_id is None:
            return True

        stationary_unit = state.units[occupant_id]
        outcome = stacking_lookup.get((unit.stacking_category, stationary_unit.stacking_category))
        return bool(outcome is not None and outcome.may_move_through)

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
    updated_units[unit.unit_id] = unit.with_position(action.destination)

    return ActionResult(ok=True, reason="ok", state=state.with_units(updated_units))


def _load_voluntary_stacking_lookup() -> dict[tuple[str, str], StackingOutcome]:
    """Load normalized lookup for voluntary stacking interactions."""

    table = load_table("stacking_voluntary")
    if not isinstance(table, StackingVoluntaryTableModel):
        raise TypeError("stacking_voluntary table did not resolve to StackingVoluntaryTableModel")

    return voluntary_stacking_lookup(table)
