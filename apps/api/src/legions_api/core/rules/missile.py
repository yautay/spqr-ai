"""Missile validation and resolution logic."""

from __future__ import annotations

from legions_api.core.actions import MissileAction, ReloadMissileAction
from legions_api.core.model.game_state import GameState
from legions_api.core.model.unit import MissileSupply
from legions_api.core.random import seeded_d10_roll
from legions_api.core.results import ActionResult, MissileDRMModifier, MissileEvent, MissileOutcome
from legions_api.core.tables.adapters import missile_class_lookup, missile_drm_lookup
from legions_api.core.tables.loader import load_table
from legions_api.core.tables.models import MissileTableModel


def resolve_missile(state: GameState, action: MissileAction) -> ActionResult:
    """Validate and resolve a direct missile attack using table-driven strengths."""

    firing_unit = state.units.get(action.firing_unit_id)
    if firing_unit is None:
        return ActionResult(ok=False, reason="firing_unit_not_found", state=state)

    target_unit = state.units.get(action.target_unit_id)
    if target_unit is None:
        return ActionResult(ok=False, reason="target_unit_not_found", state=state)

    if firing_unit.side != state.active_side:
        return ActionResult(ok=False, reason="wrong_active_side", state=state)

    if firing_unit.side == target_unit.side:
        return ActionResult(ok=False, reason="target_not_enemy", state=state)

    if firing_unit.missile_class_id is None:
        return ActionResult(ok=False, reason="firing_unit_has_no_missile", state=state)

    if action.fire_mode == "active" and action.reaction_trigger is not None:
        return ActionResult(ok=False, reason="invalid_reaction_trigger", state=state)

    if action.fire_mode == "reaction" and action.reaction_trigger is None:
        return ActionResult(ok=False, reason="missing_reaction_trigger", state=state)

    if firing_unit.missile_supply == MissileSupply.NO:
        return ActionResult(ok=False, reason="missile_supply_empty", state=state)

    table = load_table("missile_range_results")
    if not isinstance(table, MissileTableModel):
        raise TypeError("missile_range_results table did not resolve to MissileTableModel")

    class_lookup = missile_class_lookup(table)
    class_row = class_lookup.get(firing_unit.missile_class_id)
    if class_row is None:
        return ActionResult(ok=False, reason="unknown_missile_class", state=state)

    drm_lookup = missile_drm_lookup(table)
    drm_breakdown: list[MissileDRMModifier] = []
    for modifier_id in action.modifier_ids:
        modifier = drm_lookup.get(modifier_id)
        if modifier is None:
            return ActionResult(ok=False, reason="unknown_missile_drm", state=state)

        drm_breakdown.append(MissileDRMModifier(id=modifier.id, drm=modifier.drm))

    total_drm = sum(modifier.drm for modifier in drm_breakdown)

    range_to_target = firing_unit.position.distance_to(target_unit.position)
    table_strength = class_row.strengths_by_range.get(range_to_target)
    if table_strength is None:
        return ActionResult(ok=False, reason="target_out_of_range", state=state)

    base_roll = seeded_d10_roll(rng_seed=state.rng_seed, rng_counter=state.rng_counter)
    modified_roll = base_roll + total_drm
    hit = modified_roll <= table_strength
    applied_cohesion_hits = 1 if hit else 0

    updated_units = dict(state.units)
    if applied_cohesion_hits:
        updated_units[target_unit.unit_id] = target_unit.with_added_cohesion_hits(applied_cohesion_hits)

    supply_before = firing_unit.missile_supply
    supply_after = _consume_supply(supply_before)
    updated_units[firing_unit.unit_id] = firing_unit.with_missile_supply(supply_after)

    events = [
        MissileEvent(
            event_type="missile_fired",
            unit_id=firing_unit.unit_id,
            target_unit_id=target_unit.unit_id,
            reaction_trigger=action.reaction_trigger,
            roll=base_roll,
            success=hit,
        ),
    ]
    if action.fire_mode == "reaction":
        events.append(
            MissileEvent(
                event_type="reaction_fire",
                unit_id=firing_unit.unit_id,
                target_unit_id=target_unit.unit_id,
                reaction_trigger=action.reaction_trigger,
                roll=base_roll,
                success=hit,
            )
        )

    if supply_before != supply_after:
        events.append(
            MissileEvent(
                event_type="supply_changed",
                unit_id=firing_unit.unit_id,
                supply_before=supply_before.value,
                supply_after=supply_after.value,
            )
        )

    updated_state = state.with_units(updated_units).with_rng_counter(state.rng_counter + 1)

    return ActionResult(
        ok=True,
        reason="ok",
        state=updated_state,
        missile_outcome=MissileOutcome(
            firing_unit_id=firing_unit.unit_id,
            target_unit_id=target_unit.unit_id,
            fire_mode=action.fire_mode,
            reaction_trigger=action.reaction_trigger,
            missile_class_id=firing_unit.missile_class_id,
            range_to_target=range_to_target,
            table_strength=table_strength,
            base_roll=base_roll,
            total_drm=total_drm,
            modified_roll=modified_roll,
            hit=hit,
            applied_cohesion_hits=applied_cohesion_hits,
            drm_breakdown=tuple(drm_breakdown),
        ),
        events=tuple(events),
    )


def resolve_reload(state: GameState, action: ReloadMissileAction) -> ActionResult:
    """Attempt to reload one unit's missile supply with deterministic roll."""

    unit = state.units.get(action.unit_id)
    if unit is None:
        return ActionResult(ok=False, reason="firing_unit_not_found", state=state)

    if unit.side != state.active_side:
        return ActionResult(ok=False, reason="wrong_active_side", state=state)

    if unit.missile_class_id is None:
        return ActionResult(ok=False, reason="firing_unit_has_no_missile", state=state)

    if unit.missile_supply == MissileSupply.NORMAL:
        return ActionResult(ok=False, reason="missile_supply_full", state=state)

    roll = seeded_d10_roll(rng_seed=state.rng_seed, rng_counter=state.rng_counter)
    target = 7 if unit.missile_supply == MissileSupply.LOW else 6
    success = roll <= target

    events: list[MissileEvent] = [
        MissileEvent(
            event_type="reload_attempt",
            unit_id=unit.unit_id,
            roll=roll,
            target=target,
            success=success,
            supply_before=unit.missile_supply.value,
            supply_after=unit.missile_supply.value,
        )
    ]

    updated_units = dict(state.units)
    if success:
        supply_after = _improve_supply(unit.missile_supply)
        updated_units[unit.unit_id] = unit.with_missile_supply(supply_after)
        events.append(
            MissileEvent(
                event_type="supply_changed",
                unit_id=unit.unit_id,
                supply_before=unit.missile_supply.value,
                supply_after=supply_after.value,
                success=True,
            )
        )

    updated_state = state.with_units(updated_units).with_rng_counter(state.rng_counter + 1)
    return ActionResult(ok=True, reason="ok", state=updated_state, events=tuple(events))


def _consume_supply(supply: MissileSupply) -> MissileSupply:
    """Apply one missile shot consumption step."""

    if supply == MissileSupply.NORMAL:
        return MissileSupply.LOW
    if supply == MissileSupply.LOW:
        return MissileSupply.NO
    return MissileSupply.NO


def _improve_supply(supply: MissileSupply) -> MissileSupply:
    """Apply one successful reload step."""

    if supply == MissileSupply.NO:
        return MissileSupply.LOW
    if supply == MissileSupply.LOW:
        return MissileSupply.NORMAL
    return MissileSupply.NORMAL
