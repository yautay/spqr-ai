"""AI-vs-AI smoke simulation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.ai.generator import resolve_candidate_action
from legions_api.ai.search import choose_action
from legions_api.core.bootstrap import create_demo_state
from legions_api.core.model.unit import Side
from legions_api.core.turn import end_turn


@dataclass(frozen=True, slots=True)
class AISmokeSummary:
    """Compact deterministic summary for smoke simulation assertions."""

    turns_played: int
    actions_executed: int
    red_actions: int
    blue_actions: int
    terminated_reason: str


def run_ai_vs_ai_smoke(
    turn_limit: int = 8,
    time_budget_ms: int = 80,
    max_candidates: int = 96,
) -> AISmokeSummary:
    """Run bounded AI-vs-AI simulation and return deterministic summary."""

    state = create_demo_state()
    actions_executed = 0
    red_actions = 0
    blue_actions = 0
    terminated_reason = "turn_limit_reached"

    for turn_index in range(turn_limit):
        side_to_move = state.active_side
        search_result = choose_action(state=state, time_budget_ms=time_budget_ms, max_candidates=max_candidates)
        if search_result.selected is None:
            terminated_reason = "no_legal_actions"
            return AISmokeSummary(
                turns_played=turn_index,
                actions_executed=actions_executed,
                red_actions=red_actions,
                blue_actions=blue_actions,
                terminated_reason=terminated_reason,
            )

        action_result = resolve_candidate_action(state, search_result.selected)
        if not action_result.ok:
            terminated_reason = "action_rejected"
            return AISmokeSummary(
                turns_played=turn_index,
                actions_executed=actions_executed,
                red_actions=red_actions,
                blue_actions=blue_actions,
                terminated_reason=terminated_reason,
            )

        actions_executed += 1
        if side_to_move == Side.RED:
            red_actions += 1
        else:
            blue_actions += 1

        state, _ = end_turn(action_result.state)

    return AISmokeSummary(
        turns_played=turn_limit,
        actions_executed=actions_executed,
        red_actions=red_actions,
        blue_actions=blue_actions,
        terminated_reason=terminated_reason,
    )
