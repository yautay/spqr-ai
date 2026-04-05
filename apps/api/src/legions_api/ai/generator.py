"""Legal action generation for AI move selection."""

from __future__ import annotations

from legions_api.ai.types import AICandidateAction
from legions_api.core.actions import MissileAction, MoveAction, ReloadMissileAction, ShockAction
from legions_api.core.model.game_state import GameState, TurnPhase
from legions_api.core.rules.facing import is_adjacent_to_unit
from legions_api.core.rules.missile import resolve_missile, resolve_reload
from legions_api.core.rules.movement import list_legal_move_options, resolve_move
from legions_api.core.rules.shock import resolve_shock


def generate_legal_actions(state: GameState, max_actions: int | None = None) -> tuple[AICandidateAction, ...]:
    """Enumerate legal actions for current active side using core rule validators."""

    if state.turn_phase == TurnPhase.ORDERS:
        return _generate_orders_actions(state, max_actions=max_actions)
    if state.turn_phase == TurnPhase.SHOCK:
        return _generate_shock_actions(state, max_actions=max_actions)
    if state.turn_phase == TurnPhase.ROUT_AND_RELOAD:
        return _generate_reload_actions(state, max_actions=max_actions)

    return ()


def _generate_orders_actions(state: GameState, max_actions: int | None = None) -> tuple[AICandidateAction, ...]:
    """Enumerate legal movement and active missile actions for orders segment."""

    candidates: list[AICandidateAction] = []
    active_units = sorted(
        (unit for unit in state.units.values() if unit.side == state.active_side),
        key=lambda unit: unit.unit_id,
    )
    enemy_units = sorted(
        (unit for unit in state.units.values() if unit.side != state.active_side),
        key=lambda unit: unit.unit_id,
    )

    for unit in active_units:
        for move_option in list_legal_move_options(state, unit.unit_id):
            move_action = MoveAction(unit_id=unit.unit_id, destination=move_option.destination)
            candidates.append(
                AICandidateAction(
                    action_type="move",
                    action=move_action,
                    summary=f"move {unit.unit_id} -> ({move_option.destination.q},{move_option.destination.r})",
                )
            )
            if _reached_limit(candidates, max_actions):
                return tuple(candidates)

        if unit.missile_class_id is not None:
            for target_unit in enemy_units:
                missile_action = MissileAction(
                    firing_unit_id=unit.unit_id,
                    target_unit_id=target_unit.unit_id,
                    fire_mode="active",
                )
                if resolve_missile(state, missile_action).ok:
                    candidates.append(
                        AICandidateAction(
                            action_type="missile",
                            action=missile_action,
                            summary=f"missile {unit.unit_id} -> {target_unit.unit_id}",
                        )
                    )
                    if _reached_limit(candidates, max_actions):
                        return tuple(candidates)

    return tuple(candidates)


def _generate_shock_actions(state: GameState, max_actions: int | None = None) -> tuple[AICandidateAction, ...]:
    """Enumerate legal shock actions for shock segment."""

    candidates: list[AICandidateAction] = []
    active_units = sorted(
        (unit for unit in state.units.values() if unit.side == state.active_side),
        key=lambda unit: unit.unit_id,
    )
    enemy_units = sorted(
        (unit for unit in state.units.values() if unit.side != state.active_side),
        key=lambda unit: unit.unit_id,
    )
    for unit in active_units:
        for target_unit in enemy_units:
            if not is_adjacent_to_unit(attacker=unit, defender=target_unit):
                continue

            shock_action = ShockAction(
                attacker_unit_id=unit.unit_id,
                defender_unit_id=target_unit.unit_id,
            )
            result = resolve_shock(state, shock_action)
            if result.ok:
                angle = result.shock_outcome.angle if result.shock_outcome is not None else "front"
                candidates.append(
                    AICandidateAction(
                        action_type="shock",
                        action=shock_action,
                        summary=f"shock {unit.unit_id} -> {target_unit.unit_id} ({angle})",
                    )
                )
                if _reached_limit(candidates, max_actions):
                    return tuple(candidates)

    return tuple(candidates)


def _generate_reload_actions(state: GameState, max_actions: int | None = None) -> tuple[AICandidateAction, ...]:
    """Enumerate legal reload actions for rout-and-reload segment."""

    candidates: list[AICandidateAction] = []
    active_units = sorted(
        (unit for unit in state.units.values() if unit.side == state.active_side),
        key=lambda unit: unit.unit_id,
    )
    for unit in active_units:
        reload_action = ReloadMissileAction(unit_id=unit.unit_id)
        if not resolve_reload(state, reload_action).ok:
            continue

        candidates.append(
            AICandidateAction(
                action_type="reload",
                action=reload_action,
                summary=f"reload {unit.unit_id}",
            )
        )
        if _reached_limit(candidates, max_actions):
            return tuple(candidates)

    return tuple(candidates)


def resolve_candidate_action(state: GameState, candidate: AICandidateAction):
    """Resolve one AI candidate action through same command pipeline as player actions."""

    if candidate.action_type == "move":
        return resolve_movement_candidate(state, candidate)
    if candidate.action_type == "missile":
        if not isinstance(candidate.action, MissileAction):
            raise TypeError("candidate action_type missile must carry MissileAction")
        return resolve_missile(state, candidate.action)
    if candidate.action_type == "reload":
        if not isinstance(candidate.action, ReloadMissileAction):
            raise TypeError("candidate action_type reload must carry ReloadMissileAction")
        return resolve_reload(state, candidate.action)

    if not isinstance(candidate.action, ShockAction):
        raise TypeError("candidate action_type shock must carry ShockAction")

    return resolve_shock(state, candidate.action)


def resolve_movement_candidate(state: GameState, candidate: AICandidateAction):
    """Resolve movement candidate helper with narrowed type branch."""

    if not isinstance(candidate.action, MoveAction):
        raise TypeError("candidate action_type move must carry MoveAction")

    return resolve_move(state, candidate.action)


def _reached_limit(candidates: list[AICandidateAction], max_actions: int | None) -> bool:
    """Return whether generator already reached configured maximum candidate count."""

    return max_actions is not None and len(candidates) >= max_actions
