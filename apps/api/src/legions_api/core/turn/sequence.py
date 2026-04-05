"""Turn sequencing and activation transitions."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.game_state import ActivationState, GameState, TurnPhase
from legions_api.core.model.leader import Leader, LeaderStatus
from legions_api.core.model.unit import Side


@dataclass(frozen=True, slots=True)
class ActivationTransition:
    """Result metadata for one activation sequence transition."""

    previous_phase: TurnPhase
    next_phase: TurnPhase
    previous_side: Side
    next_side: Side
    previous_turn: int
    next_turn: int


def advance_activation_step(state: GameState) -> tuple[GameState, ActivationTransition]:
    """Advance one deterministic activation step in current turn."""

    previous_phase = state.turn_phase
    previous_side = state.active_side
    previous_turn = state.turn_number

    if previous_phase == TurnPhase.ORDERS:
        next_state = state.with_turn_phase(TurnPhase.SHOCK)
    elif previous_phase == TurnPhase.SHOCK:
        next_state = state.with_turn_phase(TurnPhase.ROUT_AND_RELOAD)
    elif previous_phase == TurnPhase.ROUT_AND_RELOAD:
        next_state = _advance_after_reload(state)
    else:
        next_side = _opposite_side(previous_side)
        turn_delta = 1 if previous_side == Side.BLUE else 0
        next_state = (
            state.with_active_side(next_side)
            .with_turn_phase(TurnPhase.ORDERS)
            .with_turn_number(state.turn_number + turn_delta)
            .with_reaction_windows(open_reaction_windows=())
        )
        next_state = _prepare_side_activation(next_state)

    return next_state, ActivationTransition(
        previous_phase=previous_phase,
        next_phase=next_state.turn_phase,
        previous_side=previous_side,
        next_side=next_state.active_side,
        previous_turn=previous_turn,
        next_turn=next_state.turn_number,
    )


def end_turn(state: GameState) -> tuple[GameState, ActivationTransition]:
    """Force-end current activation and start opposite side orders phase."""

    previous_side = state.active_side
    next_side = _opposite_side(previous_side)
    turn_delta = 1 if previous_side == Side.BLUE else 0
    next_state = (
        state.with_active_side(next_side)
        .with_turn_phase(TurnPhase.ORDERS)
        .with_turn_number(state.turn_number + turn_delta)
        .with_reaction_windows(open_reaction_windows=())
    )
    next_state = _prepare_side_activation(next_state)

    return next_state, ActivationTransition(
        previous_phase=state.turn_phase,
        next_phase=next_state.turn_phase,
        previous_side=previous_side,
        next_side=next_side,
        previous_turn=state.turn_number,
        next_turn=next_state.turn_number,
    )


def _opposite_side(side: Side) -> Side:
    """Return deterministic opposite battle side."""

    return Side.BLUE if side == Side.RED else Side.RED


def _advance_after_reload(state: GameState) -> GameState:
    """Advance from reload either to next leader, withdrawal, or next side."""

    leaders = dict(state.leaders)
    active_leader = state.current_active_leader()
    if active_leader is not None:
        leaders[active_leader.leader_id] = active_leader.with_status(LeaderStatus.FINISHED)

    inactive_current_side = sorted(
        (leader for leader in leaders.values() if leader.side == state.active_side and leader.status == LeaderStatus.INACTIVE),
        key=lambda leader: (leader.initiative, leader.leader_id),
    )
    if inactive_current_side:
        next_leader = inactive_current_side[0]
        leaders[next_leader.leader_id] = next_leader.with_status(LeaderStatus.ACTIVE)
        updated_state = state.with_leaders(leaders).with_turn_phase(TurnPhase.ORDERS).with_reaction_windows(open_reaction_windows=())
        return updated_state.with_activation(
            ActivationState(
                leader_id=next_leader.leader_id,
                orders_remaining=next_leader.initiative,
                line_commands_remaining=max(0, next_leader.line_command),
                activated_leader_ids=(*state.activation.activated_leader_ids, next_leader.leader_id),
            )
        )

    updated_state = state.with_leaders(_finish_side_leaders(leaders=leaders, side=state.active_side))
    if state.active_side == Side.RED:
        return updated_state.with_turn_phase(TurnPhase.WITHDRAWAL).with_reaction_windows(open_reaction_windows=()).with_activation(ActivationState())

    next_state = (
        updated_state.with_active_side(Side.RED)
        .with_turn_number(state.turn_number + 1)
        .with_turn_phase(TurnPhase.ORDERS)
        .with_reaction_windows(open_reaction_windows=())
    )
    return _prepare_side_activation(_reset_leaders_for_new_turn(next_state))


def _prepare_side_activation(state: GameState) -> GameState:
    """Select active-side leader with lowest initiative and arm activation budget."""

    leaders = dict(state.leaders)
    eligible = sorted(
        (leader for leader in leaders.values() if leader.side == state.active_side and leader.status == LeaderStatus.INACTIVE),
        key=lambda leader: (leader.initiative, leader.leader_id),
    )
    if not eligible:
        return state.with_activation(ActivationState())

    selected = eligible[0]
    leaders[selected.leader_id] = selected.with_status(LeaderStatus.ACTIVE)
    return state.with_leaders(leaders).with_activation(
        ActivationState(
            leader_id=selected.leader_id,
            orders_remaining=selected.initiative,
            line_commands_remaining=max(0, selected.line_command),
            activated_leader_ids=(selected.leader_id,),
        )
    )


def _reset_leaders_for_new_turn(state: GameState) -> GameState:
    """Reset all leaders to inactive at start of a new turn."""

    leaders = {leader_id: leader.with_status(LeaderStatus.INACTIVE) for leader_id, leader in state.leaders.items()}
    return state.with_leaders(leaders)


def _finish_side_leaders(leaders: dict[str, Leader], side: Side) -> dict[str, Leader]:
    """Mark all leaders of one side as finished for current turn."""

    updated: dict[str, Leader] = {}
    for leader_id, leader in leaders.items():
        if leader.side == side and leader.status != LeaderStatus.FINISHED:
            updated[leader_id] = leader.with_status(LeaderStatus.FINISHED)
        else:
            updated[leader_id] = leader
    return updated
