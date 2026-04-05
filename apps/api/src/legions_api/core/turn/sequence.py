"""Turn sequencing and activation transitions."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.game_state import GameState, TurnPhase
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
    else:
        next_side = _opposite_side(previous_side)
        turn_delta = 1 if previous_side == Side.BLUE else 0
        next_state = (
            state.with_active_side(next_side)
            .with_turn_phase(TurnPhase.ORDERS)
            .with_turn_number(state.turn_number + turn_delta)
            .with_reaction_windows(open_reaction_windows=())
        )

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
