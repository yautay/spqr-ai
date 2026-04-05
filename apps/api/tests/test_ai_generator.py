"""Tests for AI legal action generation."""

from legions_api.ai.generator import generate_legal_actions
from legions_api.core.bootstrap import create_demo_state


def test_generate_legal_actions_returns_non_empty_candidates() -> None:
    """AI generator should produce at least one legal candidate for demo state."""

    state = create_demo_state()

    actions = generate_legal_actions(state)

    assert len(actions) > 0
    assert all(action.action_type in {"move", "missile", "reload", "shock"} for action in actions)


def test_generate_legal_actions_includes_move_and_missile_for_demo_state() -> None:
    """Demo setup should expose at least one move and missile candidate."""

    state = create_demo_state()

    actions = generate_legal_actions(state)

    action_types = {action.action_type for action in actions}
    assert "move" in action_types
    assert "missile" in action_types


def test_generate_legal_actions_respects_max_actions_limit() -> None:
    """AI generator should stop after configured candidate cap."""

    state = create_demo_state()

    actions = generate_legal_actions(state, max_actions=2)

    assert len(actions) == 2
