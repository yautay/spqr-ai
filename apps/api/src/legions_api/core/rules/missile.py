"""Missile validation and resolution logic."""

from __future__ import annotations

from legions_api.core.actions import MissileAction
from legions_api.core.model.game_state import GameState
from legions_api.core.results import ActionResult, MissileDRMModifier, MissileOutcome
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

    base_roll = _seeded_d10_roll(rng_seed=state.rng_seed, rng_counter=state.rng_counter)
    modified_roll = base_roll + total_drm
    hit = modified_roll <= table_strength
    applied_cohesion_hits = 1 if hit else 0

    updated_units = dict(state.units)
    if applied_cohesion_hits:
        updated_units[target_unit.unit_id] = target_unit.with_added_cohesion_hits(applied_cohesion_hits)

    updated_state = state.with_units(updated_units).with_rng_counter(state.rng_counter + 1)

    return ActionResult(
        ok=True,
        reason="ok",
        state=updated_state,
        missile_outcome=MissileOutcome(
            firing_unit_id=firing_unit.unit_id,
            target_unit_id=target_unit.unit_id,
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
    )


def _seeded_d10_roll(rng_seed: int, rng_counter: int) -> int:
    """Return deterministic seeded d10 roll for current game RNG state."""

    value = (1664525 * rng_seed + 1013904223 * rng_counter) % (2**32)
    return (value % 10) + 1
