"""Tests for AI-vs-AI smoke simulation utility."""

from legions_api.ai.smoke import run_ai_vs_ai_smoke


def test_ai_vs_ai_smoke_runs_deterministically() -> None:
    """Smoke summary should be deterministic across repeated runs."""

    first = run_ai_vs_ai_smoke(turn_limit=4, time_budget_ms=80, max_candidates=48)
    second = run_ai_vs_ai_smoke(turn_limit=4, time_budget_ms=80, max_candidates=48)

    assert first == second
    assert first.actions_executed >= 1
    assert first.red_actions + first.blue_actions == first.actions_executed
