"""Shock combat validation and resolution logic."""

from __future__ import annotations

from legions_api.core.actions import ShockAction
from legions_api.core.model.game_state import GameState
from legions_api.core.random import seeded_d10_roll
from legions_api.core.results import ActionResult, ShockModifier, ShockOutcome
from legions_api.core.tables.adapters import (
    ShockCRTCellLookup,
    clash_column_lookup,
    shock_column_adjustment_lookup,
    shock_crt_lookup,
    shock_superiority_lookup,
)
from legions_api.core.tables.loader import load_table
from legions_api.core.tables.models import ClashColumnsTableModel, ShockCRTTableModel, ShockSuperiorityTableModel


def resolve_shock(state: GameState, action: ShockAction) -> ActionResult:
    """Validate and resolve one adjacent shock attack."""

    attacker = state.units.get(action.attacker_unit_id)
    if attacker is None:
        return ActionResult(ok=False, reason="attacker_unit_not_found", state=state)

    defender = state.units.get(action.defender_unit_id)
    if defender is None:
        return ActionResult(ok=False, reason="defender_unit_not_found", state=state)

    if attacker.side != state.active_side:
        return ActionResult(ok=False, reason="wrong_active_side", state=state)

    if attacker.side == defender.side:
        return ActionResult(ok=False, reason="target_not_enemy", state=state)

    if attacker.position.distance_to(defender.position) != 1:
        return ActionResult(ok=False, reason="shock_not_adjacent", state=state)

    superiority_table = load_table("shock_superiority")
    clash_table = load_table("clash_columns")
    crt_table = load_table("shock_crt")
    if not isinstance(superiority_table, ShockSuperiorityTableModel):
        raise TypeError("shock_superiority table did not resolve to ShockSuperiorityTableModel")
    if not isinstance(clash_table, ClashColumnsTableModel):
        raise TypeError("clash_columns table did not resolve to ClashColumnsTableModel")
    if not isinstance(crt_table, ShockCRTTableModel):
        raise TypeError("shock_crt table did not resolve to ShockCRTTableModel")

    clash_lookup = clash_column_lookup(clash_table)
    superiority_lookup = shock_superiority_lookup(superiority_table)
    adjustment_lookup = shock_column_adjustment_lookup(crt_table)
    crt_lookup = shock_crt_lookup(crt_table)

    attacker_type = attacker.shock_type
    defender_type = defender.shock_type
    base_column = clash_lookup.get((attacker_type, defender_type, action.angle))
    if base_column is None:
        return ActionResult(ok=False, reason="unknown_clash_column", state=state)

    modifier_ids: list[str] = []
    superiority_shift = superiority_lookup.get((attacker_type, defender_type), 0)
    if superiority_shift > 0:
        modifier_ids.append("superiority_attacker")
    elif superiority_shift < 0:
        modifier_ids.append("superiority_defender")

    for modifier_id in action.modifier_ids:
        if modifier_id not in modifier_ids:
            modifier_ids.append(modifier_id)

    modifier_breakdown: list[ShockModifier] = []
    total_shift = 0
    for modifier_id in modifier_ids:
        modifier = adjustment_lookup.get(modifier_id)
        if modifier is None:
            return ActionResult(ok=False, reason="unknown_shock_modifier", state=state)

        total_shift += modifier.shift
        modifier_breakdown.append(ShockModifier(id=modifier.id, shift=modifier.shift))

    crt_columns = sorted(int(column) for column in crt_table.columns)
    final_column = max(crt_columns[0], min(crt_columns[-1], base_column + total_shift))
    roll = seeded_d10_roll(rng_seed=state.rng_seed, rng_counter=state.rng_counter)
    crt_cell = _resolve_crt_cell(crt_table=crt_table, crt_lookup=crt_lookup, column=final_column, roll=roll)

    updated_units = dict(state.units)
    updated_units[attacker.unit_id] = attacker.with_added_cohesion_hits(crt_cell.attacker_hits)
    updated_units[defender.unit_id] = defender.with_added_cohesion_hits(crt_cell.defender_hits)
    updated_state = state.with_units(updated_units).with_rng_counter(state.rng_counter + 1)

    return ActionResult(
        ok=True,
        reason="ok",
        state=updated_state,
        shock_outcome=ShockOutcome(
            attacker_unit_id=attacker.unit_id,
            defender_unit_id=defender.unit_id,
            angle=action.angle,
            attacker_type=attacker_type,
            defender_type=defender_type,
            base_column=base_column,
            total_shift=total_shift,
            final_column=final_column,
            roll=roll,
            attacker_hits=crt_cell.attacker_hits,
            defender_hits=crt_cell.defender_hits,
            modifier_breakdown=tuple(modifier_breakdown),
        ),
    )


def _resolve_crt_cell(
    crt_table: ShockCRTTableModel,
    crt_lookup: dict[tuple[int, int], ShockCRTCellLookup],
    column: int,
    roll: int,
) -> ShockCRTCellLookup:
    """Resolve sparse CRT row/column into one normalized cell."""

    row_map = crt_table.cells.get(str(column))
    if row_map is None:
        available_columns = sorted(int(raw_column) for raw_column in crt_table.cells)
        lower_or_equal_columns = [value for value in available_columns if value <= column]
        nearest_column = lower_or_equal_columns[-1] if lower_or_equal_columns else available_columns[0]
        row_map = crt_table.cells[str(nearest_column)]
        column = nearest_column

    available_rows = sorted(int(raw_row) for raw_row in row_map)
    matching_rows = [value for value in available_rows if value <= roll]
    selected_row = matching_rows[-1] if matching_rows else available_rows[0]

    return crt_lookup[(column, selected_row)]
