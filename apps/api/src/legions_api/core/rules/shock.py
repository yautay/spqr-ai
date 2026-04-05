"""Shock combat validation and resolution logic."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.actions import ShockAction
from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.unit import Unit
from legions_api.core.random import seeded_d10_roll
from legions_api.core.results import ActionResult, MoraleOutcome, PursuitOutcome, ShockModifier, ShockOutcome, ShockPreview
from legions_api.core.tables.adapters import (
    ShockCRTCellLookup,
    clash_column_lookup,
    shock_column_adjustment_lookup,
    shock_crt_lookup,
    shock_superiority_lookup,
)
from legions_api.core.tables.loader import load_table
from legions_api.core.tables.models import ClashColumnsTableModel, ShockCRTTableModel, ShockSuperiorityTableModel


@dataclass(frozen=True, slots=True)
class _ShockResolutionContext:
    attacker: Unit
    defender: Unit
    attacker_type: str
    defender_type: str
    base_column: int
    total_shift: int
    final_column: int
    modifier_breakdown: tuple[ShockModifier, ...]
    crt_table: ShockCRTTableModel
    crt_lookup: dict[tuple[int, int], ShockCRTCellLookup]


def resolve_shock(state: GameState, action: ShockAction) -> ActionResult:
    """Validate and resolve one adjacent shock attack."""

    context, reason = _build_shock_context(state, action)
    if context is None:
        return ActionResult(ok=False, reason=reason, state=state)

    roll = seeded_d10_roll(rng_seed=state.rng_seed, rng_counter=state.rng_counter)
    next_rng_counter = state.rng_counter + 1
    crt_cell = _resolve_crt_cell(crt_table=context.crt_table, crt_lookup=context.crt_lookup, column=context.final_column, roll=roll)

    updated_units = dict(state.units)
    updated_attacker = context.attacker.with_added_cohesion_hits(crt_cell.attacker_hits)
    updated_defender = context.defender.with_added_cohesion_hits(crt_cell.defender_hits)
    updated_units[context.attacker.unit_id] = updated_attacker
    updated_units[context.defender.unit_id] = updated_defender

    morale_outcomes: list[MoraleOutcome] = []
    if crt_cell.attacker_hits > 0:
        morale_outcome, updated_attacker, next_rng_counter = _resolve_morale_check(
            unit=updated_attacker,
            rng_seed=state.rng_seed,
            rng_counter=next_rng_counter,
        )
        updated_units[context.attacker.unit_id] = updated_attacker
        morale_outcomes.append(morale_outcome)

    if crt_cell.defender_hits > 0:
        morale_outcome, updated_defender, next_rng_counter = _resolve_morale_check(
            unit=updated_defender,
            rng_seed=state.rng_seed,
            rng_counter=next_rng_counter,
        )
        updated_units[context.defender.unit_id] = updated_defender
        morale_outcomes.append(morale_outcome)

    retreat_results = _resolve_routs(
        state=state,
        attacker_id=context.attacker.unit_id,
        defender_id=context.defender.unit_id,
        units=updated_units,
        morale_outcomes=morale_outcomes,
    )
    updated_units = retreat_results.units
    morale_outcomes = retreat_results.morale_outcomes

    pursuit_outcome = _resolve_pursuit(
        state=state,
        attacker=updated_attacker,
        defender=updated_defender,
        units=updated_units,
        morale_outcomes=morale_outcomes,
    )
    updated_units = pursuit_outcome.units

    updated_state = state.with_units(updated_units).with_rng_counter(next_rng_counter)

    return ActionResult(
        ok=True,
        reason="ok",
        state=updated_state,
        shock_outcome=ShockOutcome(
            attacker_unit_id=context.attacker.unit_id,
            defender_unit_id=context.defender.unit_id,
            angle=action.angle,
            attacker_type=context.attacker_type,
            defender_type=context.defender_type,
            base_column=context.base_column,
            total_shift=context.total_shift,
            final_column=context.final_column,
            roll=roll,
            attacker_hits=crt_cell.attacker_hits,
            defender_hits=crt_cell.defender_hits,
            modifier_breakdown=context.modifier_breakdown,
        ),
        morale_outcomes=tuple(morale_outcomes),
        pursuit_outcome=pursuit_outcome.outcome,
    )


def preview_shock(state: GameState, action: ShockAction) -> tuple[ShockPreview | None, str]:
    """Compute read-only shock preview metadata for current state and command."""

    context, reason = _build_shock_context(state, action)
    if context is None:
        return None, reason

    return (
        ShockPreview(
            attacker_unit_id=context.attacker.unit_id,
            defender_unit_id=context.defender.unit_id,
            angle=action.angle,
            attacker_type=context.attacker_type,
            defender_type=context.defender_type,
            base_column=context.base_column,
            total_shift=context.total_shift,
            final_column=context.final_column,
            modifier_breakdown=context.modifier_breakdown,
        ),
        "ok",
    )


def _build_shock_context(state: GameState, action: ShockAction) -> tuple[_ShockResolutionContext | None, str]:
    """Validate static shock inputs and return metadata shared by preview and resolve."""

    attacker = state.units.get(action.attacker_unit_id)
    if attacker is None:
        return None, "attacker_unit_not_found"

    defender = state.units.get(action.defender_unit_id)
    if defender is None:
        return None, "defender_unit_not_found"

    if attacker.side != state.active_side:
        return None, "wrong_active_side"

    if attacker.side == defender.side:
        return None, "target_not_enemy"

    if attacker.position.distance_to(defender.position) != 1:
        return None, "shock_not_adjacent"

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
        return None, "unknown_clash_column"

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
            return None, "unknown_shock_modifier"

        total_shift += modifier.shift
        modifier_breakdown.append(ShockModifier(id=modifier.id, shift=modifier.shift))

    crt_columns = sorted(int(column) for column in crt_table.columns)
    final_column = max(crt_columns[0], min(crt_columns[-1], base_column + total_shift))

    return (
        _ShockResolutionContext(
            attacker=attacker,
            defender=defender,
            attacker_type=attacker_type,
            defender_type=defender_type,
            base_column=base_column,
            total_shift=total_shift,
            final_column=final_column,
            modifier_breakdown=tuple(modifier_breakdown),
            crt_table=crt_table,
            crt_lookup=crt_lookup,
        ),
        "ok",
    )


def _resolve_morale_check(
    unit: Unit,
    rng_seed: int,
    rng_counter: int,
) -> tuple[MoraleOutcome, Unit, int]:
    """Resolve one morale check after shock hits are applied."""

    target = max(1, unit.tq - unit.cohesion_hits)
    roll = seeded_d10_roll(rng_seed=rng_seed, rng_counter=rng_counter)
    passed = roll <= target
    became_routed = False
    updated_unit = unit
    if not passed:
        updated_unit = unit.with_added_cohesion_hits(1)
        if not updated_unit.is_routed:
            updated_unit = updated_unit.with_routed(True)
            became_routed = True

    outcome = MoraleOutcome(
        unit_id=unit.unit_id,
        source="shock",
        target=target,
        roll=roll,
        passed=passed,
        became_routed=became_routed,
        retreated=False,
        eliminated=False,
    )
    return outcome, updated_unit, rng_counter + 1


class _RetreatResolution:
    """Internal container for rout movement resolution updates."""

    def __init__(self, units: dict[str, Unit], morale_outcomes: list[MoraleOutcome]) -> None:
        self.units = units
        self.morale_outcomes = morale_outcomes


def _resolve_routs(
    state: GameState,
    attacker_id: str,
    defender_id: str,
    units: dict[str, Unit],
    morale_outcomes: list[MoraleOutcome],
) -> _RetreatResolution:
    """Resolve one-hex rout retreat or elimination for newly routed units."""

    updated_units = dict(units)
    updated_outcomes = list(morale_outcomes)

    opponents = {
        attacker_id: defender_id,
        defender_id: attacker_id,
    }
    for index, outcome in enumerate(updated_outcomes):
        if not outcome.became_routed:
            continue

        unit = updated_units.get(outcome.unit_id)
        opponent = updated_units.get(opponents[outcome.unit_id])
        if unit is None or opponent is None:
            continue

        destination = _retreat_destination(unit=unit, enemy=opponent)
        occupied_hexes = {occupant.position for occupant in updated_units.values() if occupant.unit_id != unit.unit_id}
        if destination is None or not state.scenario_map.contains(destination) or destination in occupied_hexes:
            del updated_units[unit.unit_id]
            updated_outcomes[index] = MoraleOutcome(
                unit_id=outcome.unit_id,
                source=outcome.source,
                target=outcome.target,
                roll=outcome.roll,
                passed=outcome.passed,
                became_routed=outcome.became_routed,
                retreated=False,
                eliminated=True,
            )
            continue

        updated_units[unit.unit_id] = unit.with_position(destination)
        updated_outcomes[index] = MoraleOutcome(
            unit_id=outcome.unit_id,
            source=outcome.source,
            target=outcome.target,
            roll=outcome.roll,
            passed=outcome.passed,
            became_routed=outcome.became_routed,
            retreated=True,
            eliminated=False,
        )

    return _RetreatResolution(units=updated_units, morale_outcomes=updated_outcomes)


def _retreat_destination(unit: Unit, enemy: Unit) -> HexCoord | None:
    """Compute one-hex retreat destination directly away from enemy unit."""

    delta_q = unit.position.q - enemy.position.q
    delta_r = unit.position.r - enemy.position.r
    if delta_q == 0 and delta_r == 0:
        return None

    return HexCoord(q=unit.position.q + delta_q, r=unit.position.r + delta_r)


class _PursuitResolution:
    """Internal container for pursuit updates after rout resolution."""

    def __init__(self, units: dict[str, Unit], outcome: PursuitOutcome | None) -> None:
        self.units = units
        self.outcome = outcome


def _resolve_pursuit(
    state: GameState,
    attacker: Unit,
    defender: Unit,
    units: dict[str, Unit],
    morale_outcomes: list[MoraleOutcome],
) -> _PursuitResolution:
    """Resolve cavalry pursuit move into enemy vacated hex after rout/elimination."""

    updated_units = dict(units)
    by_unit_id = {outcome.unit_id: outcome for outcome in morale_outcomes}
    defender_outcome = by_unit_id.get(defender.unit_id)
    if not attacker.pursuit_capable:
        return _PursuitResolution(units=updated_units, outcome=None)
    if attacker.unit_id not in updated_units:
        return _PursuitResolution(units=updated_units, outcome=None)
    if defender_outcome is None:
        return _PursuitResolution(units=updated_units, outcome=None)
    if defender_outcome.passed:
        return _PursuitResolution(units=updated_units, outcome=None)

    if defender.position in {unit.position for unit in updated_units.values() if unit.unit_id != attacker.unit_id}:
        return _PursuitResolution(units=updated_units, outcome=None)

    pursuing_unit = updated_units[attacker.unit_id]
    updated_units[attacker.unit_id] = pursuing_unit.with_position(defender.position)
    _ = state
    return _PursuitResolution(
        units=updated_units,
        outcome=PursuitOutcome(unit_id=attacker.unit_id, destination=defender.position),
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
