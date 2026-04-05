"""Tests for turn and activation sequencing helpers."""

from legions_api.core.bootstrap import create_demo_state
from legions_api.core.model.game_state import TurnPhase
from legions_api.core.model.unit import Side
from legions_api.core.turn import advance_activation_step, end_turn


def test_advance_activation_moves_orders_to_shock() -> None:
    """Advancing orders segment should move state into shock phase."""

    state = create_demo_state()

    next_state, transition = advance_activation_step(state)

    assert transition.previous_phase == TurnPhase.ORDERS
    assert transition.next_phase == TurnPhase.SHOCK
    assert transition.previous_side == next_state.active_side
    assert next_state.turn_number == 1


def test_advance_activation_moves_shock_to_reload() -> None:
    """Advancing shock segment should move state into rout-and-reload phase."""

    state = create_demo_state().with_turn_phase(TurnPhase.SHOCK)

    next_state, transition = advance_activation_step(state)

    assert transition.previous_phase == TurnPhase.SHOCK
    assert transition.next_phase == TurnPhase.ROUT_AND_RELOAD
    assert next_state.active_side == Side.RED
    assert next_state.turn_number == 1


def test_advance_activation_moves_to_next_side_after_reload() -> None:
    """Advancing reload segment should switch active side and reset to orders."""

    state = create_demo_state().with_turn_phase(TurnPhase.ROUT_AND_RELOAD)

    next_state, transition = advance_activation_step(state)

    assert transition.previous_side == Side.RED
    assert transition.next_side == Side.BLUE
    assert next_state.turn_phase == TurnPhase.ORDERS
    assert next_state.turn_number == 1


def test_end_turn_from_blue_increments_turn_counter() -> None:
    """Ending blue side should start new turn for red side."""

    state = create_demo_state().with_active_side(Side.BLUE).with_turn_number(4).with_turn_phase(TurnPhase.SHOCK)

    next_state, transition = end_turn(state)

    assert transition.previous_turn == 4
    assert transition.next_turn == 5
    assert next_state.active_side == Side.RED
    assert next_state.turn_phase == TurnPhase.ORDERS
