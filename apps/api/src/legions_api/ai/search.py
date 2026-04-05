"""Bounded shallow AI search for legal candidate actions."""

from __future__ import annotations

from time import monotonic

from legions_api.ai.evaluator import evaluate_state
from legions_api.ai.generator import generate_legal_actions, resolve_candidate_action
from legions_api.ai.types import AICandidateAction, AIScoredCandidate, AISearchResult
from legions_api.core.model.game_state import GameState


def choose_action(
    state: GameState,
    time_budget_ms: int = 150,
    max_candidates: int = 128,
) -> AISearchResult:
    """Select one action using one-ply bounded search and heuristic evaluation."""

    started_at = monotonic()
    candidates = generate_legal_actions(state, max_actions=max_candidates)
    if not candidates:
        return AISearchResult(selected=None, considered_actions=0, elapsed_ms=0, scored_candidates=())

    scored_candidates: list[AIScoredCandidate] = []
    selected: AICandidateAction | None = None
    selected_score: float | None = None

    for candidate in candidates:
        if _elapsed_ms(started_at) >= time_budget_ms and scored_candidates:
            break

        result = resolve_candidate_action(state, candidate)
        if not result.ok:
            continue

        score = evaluate_state(result.state, perspective=state.active_side)
        scored_candidate = AIScoredCandidate(candidate=candidate, score=score)
        scored_candidates.append(scored_candidate)

        if selected_score is None or score > selected_score:
            selected = candidate
            selected_score = score

    sorted_candidates = tuple(sorted(scored_candidates, key=lambda item: item.score, reverse=True))
    return AISearchResult(
        selected=selected,
        considered_actions=len(sorted_candidates),
        elapsed_ms=_elapsed_ms(started_at),
        scored_candidates=sorted_candidates,
    )


def _elapsed_ms(started_at: float) -> int:
    """Return elapsed milliseconds since monotonic start timestamp."""

    return int((monotonic() - started_at) * 1000)
