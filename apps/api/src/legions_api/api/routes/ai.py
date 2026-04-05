"""AI decision routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Body, Depends

from legions_api.ai.generator import resolve_candidate_action
from legions_api.ai.search import choose_action
from legions_api.api.dependencies import get_event_stream, get_game_store
from legions_api.api.event_stream import GameEventStream
from legions_api.api.mapper import to_ai_move_response_payload
from legions_api.api.schemas import AIMoveRequestPayload, AIMoveResponsePayload, GameEventPayload
from legions_api.api.state_store import GameStateStore

router = APIRouter(prefix="/ai", tags=["ai"])

AIEventType = Literal["ai_thinking", "ai_move_selected"]


@router.post("/move", response_model=AIMoveResponsePayload)
async def ai_move(
    payload: AIMoveRequestPayload = Body(default_factory=AIMoveRequestPayload),
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
) -> AIMoveResponsePayload:
    """Select and execute one bounded AI move for current active side."""

    event_stream.publish(
        _build_ai_event(
            event_type="ai_thinking",
            ok=True,
            reason="ok",
            details={
                "time_budget_ms": payload.time_budget_ms,
                "max_candidates": payload.max_candidates,
            },
        )
    )

    search_result = choose_action(
        state=store.state,
        time_budget_ms=payload.time_budget_ms,
        max_candidates=payload.max_candidates,
    )
    if search_result.selected is None:
        event_stream.publish(
            _build_ai_event(
                event_type="ai_move_selected",
                ok=False,
                reason="no_legal_actions",
                details={"considered_actions": search_result.considered_actions},
            )
        )
        return to_ai_move_response_payload(search_result=search_result, action_result=None, reason="no_legal_actions")

    action_result = resolve_candidate_action(store.state, search_result.selected)
    if action_result.ok:
        store.replace(action_result.state)

    event_stream.publish(
        _build_ai_event(
            event_type="ai_move_selected",
            ok=action_result.ok,
            reason=action_result.reason,
            details={
                "action_type": search_result.selected.action_type,
                "summary": search_result.selected.summary,
                "considered_actions": search_result.considered_actions,
            },
        )
    )
    return to_ai_move_response_payload(
        search_result=search_result,
        action_result=action_result,
        reason=action_result.reason,
    )


def _build_ai_event(
    event_type: AIEventType,
    ok: bool,
    reason: str,
    details: dict[str, str | int | bool | None],
) -> GameEventPayload:
    """Create one AI-specific websocket event payload."""

    return GameEventPayload(
        event_id=str(uuid4()),
        timestamp=datetime.now(tz=UTC).isoformat(),
        event_type=event_type,
        ok=ok,
        reason=reason,
        details=details,
    )
