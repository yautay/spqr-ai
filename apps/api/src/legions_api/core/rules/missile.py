"""Missile validation and resolution logic."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.actions import MissileAction, ReloadMissileAction
from legions_api.core.model.game_state import GameState, TurnPhase
from legions_api.core.model.map import TerrainType
from legions_api.core.model.unit import MissileSupply, Unit
from legions_api.core.random import seeded_d10_roll
from legions_api.core.results import ActionResult, DomainEvent, MissileDRMModifier, MissileOutcome, MissilePreview
from legions_api.core.rules.los import has_line_of_sight
from legions_api.core.tables.adapters import MissileClassLookup, missile_class_lookup, missile_drm_lookup
from legions_api.core.tables.loader import load_table
from legions_api.core.tables.models import MissileTableModel


@dataclass(frozen=True, slots=True)
class _MissileResolutionContext:
    firing_unit: Unit
    target_unit: Unit
    class_row: MissileClassLookup
    range_to_target: int
    table_strength: int
    drm_breakdown: tuple[MissileDRMModifier, ...]
    total_drm: int


def resolve_missile(state: GameState, action: MissileAction) -> ActionResult:
    """Validate and resolve a direct missile attack using table-driven strengths."""

    context, reason = _build_missile_context(state, action)
    if context is None:
        return ActionResult(ok=False, reason=reason, state=state)

    base_roll = seeded_d10_roll(rng_seed=state.rng_seed, rng_counter=state.rng_counter)
    modified_roll = base_roll + context.total_drm
    hit = modified_roll <= context.table_strength
    applied_cohesion_hits = 1 if hit else 0

    updated_units = dict(state.units)
    if applied_cohesion_hits:
        updated_units[context.target_unit.unit_id] = context.target_unit.with_added_cohesion_hits(applied_cohesion_hits)

    supply_before = context.firing_unit.missile_supply
    supply_after = _consume_supply(supply_before)
    updated_units[context.firing_unit.unit_id] = context.firing_unit.with_missile_supply(supply_after)

    events = [
        DomainEvent(
            event_type="missile_fired",
            details={
                "unit_id": context.firing_unit.unit_id,
                "target_unit_id": context.target_unit.unit_id,
                "reaction_trigger": action.reaction_trigger,
                "roll": base_roll,
                "success": hit,
            },
        ),
    ]
    if action.fire_mode == "reaction":
        events.append(
            DomainEvent(
                event_type="reaction_fire",
                details={
                    "unit_id": context.firing_unit.unit_id,
                    "target_unit_id": context.target_unit.unit_id,
                    "reaction_trigger": action.reaction_trigger,
                    "roll": base_roll,
                    "success": hit,
                },
            )
        )

    if supply_before != supply_after:
        events.append(
            DomainEvent(
                event_type="supply_changed",
                details={
                    "unit_id": context.firing_unit.unit_id,
                    "supply_before": supply_before.value,
                    "supply_after": supply_after.value,
                },
            )
        )

    updated_state = state.with_units(updated_units).with_rng_counter(state.rng_counter + 1)
    if action.fire_mode == "active":
        updated_state = updated_state.with_activation(
            state.activation.__class__(
                leader_id=state.activation.leader_id,
                orders_remaining=max(0, state.activation.orders_remaining - 1),
                line_commands_remaining=state.activation.line_commands_remaining,
                moved_unit_ids=state.activation.moved_unit_ids,
                fired_unit_ids=(*state.activation.fired_unit_ids, context.firing_unit.unit_id),
                shocked_unit_ids=state.activation.shocked_unit_ids,
                activated_leader_ids=state.activation.activated_leader_ids,
            )
        )
    if action.fire_mode == "reaction" and action.reaction_trigger is not None:
        updated_state = updated_state.mark_reaction_window_spent(
            firing_unit_id=context.firing_unit.unit_id,
            target_unit_id=context.target_unit.unit_id,
            reaction_trigger=action.reaction_trigger,
        )
        events.append(
            DomainEvent(
                event_type="reaction_window_spent",
                details={
                    "unit_id": context.firing_unit.unit_id,
                    "target_unit_id": context.target_unit.unit_id,
                    "reaction_trigger": action.reaction_trigger,
                },
            )
        )

    return ActionResult(
        ok=True,
        reason="ok",
        state=updated_state,
        missile_outcome=MissileOutcome(
            firing_unit_id=context.firing_unit.unit_id,
            target_unit_id=context.target_unit.unit_id,
            fire_mode=action.fire_mode,
            reaction_trigger=action.reaction_trigger,
            missile_class_id=context.class_row.class_id,
            range_to_target=context.range_to_target,
            table_strength=context.table_strength,
            base_roll=base_roll,
            total_drm=context.total_drm,
            modified_roll=modified_roll,
            hit=hit,
            applied_cohesion_hits=applied_cohesion_hits,
            drm_breakdown=context.drm_breakdown,
        ),
        events=tuple(events),
    )


def preview_missile(state: GameState, action: MissileAction) -> tuple[MissilePreview | None, str]:
    """Compute read-only missile preview metadata for current state and command."""

    context, reason = _build_missile_context(state, action)
    if context is None:
        return None, reason

    return (
        MissilePreview(
            firing_unit_id=context.firing_unit.unit_id,
            target_unit_id=context.target_unit.unit_id,
            fire_mode=action.fire_mode,
            reaction_trigger=action.reaction_trigger,
            missile_class_id=context.class_row.class_id,
            range_to_target=context.range_to_target,
            table_strength=context.table_strength,
            total_drm=context.total_drm,
            hit_threshold=context.table_strength - context.total_drm,
            drm_breakdown=context.drm_breakdown,
        ),
        "ok",
    )


def resolve_reload(state: GameState, action: ReloadMissileAction) -> ActionResult:
    """Attempt to reload one unit's missile supply with deterministic roll."""

    unit = state.units.get(action.unit_id)
    if unit is None:
        return ActionResult(ok=False, reason="firing_unit_not_found", state=state)

    if state.turn_phase != TurnPhase.ROUT_AND_RELOAD:
        return ActionResult(ok=False, reason="wrong_turn_phase", state=state)

    if unit.side != state.active_side:
        return ActionResult(ok=False, reason="wrong_active_side", state=state)

    if unit.missile_class_id is None:
        return ActionResult(ok=False, reason="firing_unit_has_no_missile", state=state)

    if unit.missile_supply == MissileSupply.NORMAL:
        return ActionResult(ok=False, reason="missile_supply_full", state=state)

    roll = seeded_d10_roll(rng_seed=state.rng_seed, rng_counter=state.rng_counter)
    target = 7 if unit.missile_supply == MissileSupply.LOW else 6
    success = roll <= target

    events: list[DomainEvent] = [
        DomainEvent(
            event_type="reload_attempt",
            details={
                "unit_id": unit.unit_id,
                "roll": roll,
                "target": target,
                "success": success,
                "supply_before": unit.missile_supply.value,
                "supply_after": unit.missile_supply.value,
            },
        )
    ]

    updated_units = dict(state.units)
    if success:
        supply_after = _improve_supply(unit.missile_supply)
        updated_units[unit.unit_id] = unit.with_missile_supply(supply_after)
        events.append(
            DomainEvent(
                event_type="supply_changed",
                details={
                    "unit_id": unit.unit_id,
                    "supply_before": unit.missile_supply.value,
                    "supply_after": supply_after.value,
                    "success": True,
                },
            )
        )

    updated_state = state.with_units(updated_units).with_rng_counter(state.rng_counter + 1)
    return ActionResult(ok=True, reason="ok", state=updated_state, events=tuple(events))


def _build_missile_context(state: GameState, action: MissileAction) -> tuple[_MissileResolutionContext | None, str]:
    """Validate static missile inputs and return metadata shared by preview and resolve."""

    firing_unit = state.units.get(action.firing_unit_id)
    if firing_unit is None:
        return None, "firing_unit_not_found"

    target_unit = state.units.get(action.target_unit_id)
    if target_unit is None:
        return None, "target_unit_not_found"

    if action.fire_mode == "active" and firing_unit.side != state.active_side:
        return None, "wrong_active_side"

    if action.fire_mode == "active" and state.turn_phase != TurnPhase.ORDERS:
        return None, "wrong_turn_phase"

    if action.fire_mode == "active":
        active_leader = state.current_active_leader()
        if active_leader is None:
            return None, "no_active_leader"
        if state.activation.orders_remaining <= 0:
            return None, "no_orders_remaining"
        if firing_unit.unit_id in state.activation.fired_unit_ids:
            return None, "unit_already_fired_this_activation"
        if active_leader.position.distance_to(firing_unit.position) > active_leader.command_range:
            return None, "unit_out_of_command_range"

    if firing_unit.side == target_unit.side:
        return None, "target_not_enemy"

    if firing_unit.missile_class_id is None:
        return None, "firing_unit_has_no_missile"

    if action.fire_mode == "active" and action.reaction_trigger is not None:
        return None, "invalid_reaction_trigger"

    if action.fire_mode == "reaction" and action.reaction_trigger is None:
        return None, "missing_reaction_trigger"

    if action.fire_mode == "reaction" and firing_unit.side == state.active_side:
        return None, "wrong_reaction_side"

    if action.fire_mode == "reaction" and action.reaction_trigger is not None:
        if state.is_reaction_window_spent(
            firing_unit_id=firing_unit.unit_id,
            target_unit_id=target_unit.unit_id,
            reaction_trigger=action.reaction_trigger,
        ):
            return None, "reaction_window_spent"

        if not state.is_reaction_window_open(
            firing_unit_id=firing_unit.unit_id,
            target_unit_id=target_unit.unit_id,
            reaction_trigger=action.reaction_trigger,
        ):
            return None, "reaction_window_unavailable"

    if firing_unit.missile_supply == MissileSupply.NO:
        return None, "missile_supply_empty"

    table = load_table("missile_range_results")
    if not isinstance(table, MissileTableModel):
        raise TypeError("missile_range_results table did not resolve to MissileTableModel")

    class_lookup = missile_class_lookup(table)
    class_row = class_lookup.get(firing_unit.missile_class_id)
    if class_row is None:
        return None, "unknown_missile_class"

    if not has_line_of_sight(state, firing_unit.position, target_unit.position):
        return None, "no_line_of_sight"

    drm_lookup = missile_drm_lookup(table)
    modifier_ids = _resolve_modifier_ids(
        auto_modifier_ids=_auto_modifier_ids(state=state, firing_unit_id=firing_unit.unit_id, target_unit_id=target_unit.unit_id),
        explicit_modifier_ids=action.modifier_ids,
    )
    drm_breakdown: list[MissileDRMModifier] = []
    for modifier_id in modifier_ids:
        modifier = drm_lookup.get(modifier_id)
        if modifier is None:
            return None, "unknown_missile_drm"

        drm_breakdown.append(MissileDRMModifier(id=modifier.id, drm=modifier.drm))

    total_drm = sum(modifier.drm for modifier in drm_breakdown)
    range_to_target = firing_unit.position.distance_to(target_unit.position)
    table_strength = class_row.strengths_by_range.get(range_to_target)
    if table_strength is None:
        return None, "target_out_of_range"

    return (
        _MissileResolutionContext(
            firing_unit=firing_unit,
            target_unit=target_unit,
            class_row=class_row,
            range_to_target=range_to_target,
            table_strength=table_strength,
            drm_breakdown=tuple(drm_breakdown),
            total_drm=total_drm,
        ),
        "ok",
    )


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


def _auto_modifier_ids(state: GameState, firing_unit_id: str, target_unit_id: str) -> tuple[str, ...]:
    """Resolve state-driven missile modifiers that should apply automatically."""

    firing_unit = state.units[firing_unit_id]
    target_unit = state.units[target_unit_id]
    target_tile = state.scenario_map.tile_at(target_unit.position)

    modifier_ids: list[str] = []
    if target_tile is not None and target_tile.terrain == TerrainType.WOODS:
        modifier_ids.append("target_woods")

    if firing_unit.missile_supply != MissileSupply.NORMAL:
        modifier_ids.append("firing_unit_depleted")

    return tuple(modifier_ids)


def _resolve_modifier_ids(auto_modifier_ids: tuple[str, ...], explicit_modifier_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Merge auto and explicit modifier ids while preserving first-seen order."""

    ordered: list[str] = []
    seen: set[str] = set()
    for modifier_id in (*auto_modifier_ids, *explicit_modifier_ids):
        if modifier_id in seen:
            continue

        seen.add(modifier_id)
        ordered.append(modifier_id)

    return tuple(ordered)
