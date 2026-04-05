"""Tests for bounded AI search selection."""

from legions_api.ai.search import choose_action
from legions_api.core.bootstrap import create_demo_state


def test_choose_action_returns_selected_candidate_for_demo_state() -> None:
    """AI search should pick one legal action in baseline state."""

    state = create_demo_state()

    result = choose_action(state=state, time_budget_ms=120, max_candidates=64)

    assert result.selected is not None
    assert result.considered_actions > 0
    assert len(result.scored_candidates) > 0


def test_choose_action_obeys_candidate_cap() -> None:
    """AI search should not evaluate beyond configured candidate cap."""

    state = create_demo_state()

    result = choose_action(state=state, time_budget_ms=120, max_candidates=2)

    assert result.considered_actions <= 2
