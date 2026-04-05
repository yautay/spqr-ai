"""Game state and action routes."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from queue import Empty
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, WebSocket, WebSocketDisconnect
from loguru import logger

from legions_api.api.dependencies import get_event_stream, get_game_store
from legions_api.api.event_stream import GameEventStream
from legions_api.api.mapper import (
    to_action_response_payload,
    to_game_state_payload,
    to_legal_moves_payload,
    to_missile_preview_response_payload,
    to_shock_preview_response_payload,
)
from legions_api.api.schemas import (
    ActionResponsePayload,
    GameEventPayload,
    GameStatePayload,
    LegalMovesPayload,
    MissileActionPayload,
    MissilePreviewResponsePayload,
    MissileReloadActionPayload,
    MoveActionPayload,
    NewGamePayload,
    RulesetsPayload,
    SetPhasePayload,
    ShockActionPayload,
    ShockPreviewResponsePayload,
)
from legions_api.api.state_store import GameStateStore
from legions_api.core.actions import MissileAction, MoveAction, ReloadMissileAction, ShockAction
from legions_api.core.model.hex import HexCoord
from legions_api.core.rules.missile import preview_missile, resolve_missile, resolve_reload
from legions_api.core.rules.movement import list_legal_move_options, resolve_move
from legions_api.core.rules.shock import preview_shock, resolve_shock
from legions_api.core.tables.loader import available_rulesets

router = APIRouter(prefix="/game", tags=["game"])

GameEventType = Literal[
    "game_reset",
    "phase_changed",
    "move_resolved",
    "missile_resolved",
    "reload_resolved",
    "shock_resolved",
    "ai_thinking",
    "ai_move_selected",
]


@router.post("/new", response_model=GameStatePayload)
async def new_game(
    payload: NewGamePayload = Body(default_factory=NewGamePayload),
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
) -> GameStatePayload:
    """Reset in-memory game and return the fresh state."""

    state = store.reset(ruleset_mode=payload.ruleset)
    event_stream.publish(
        _build_game_event(
            event_type="game_reset",
            ok=True,
            reason="ok",
            details={"ruleset": payload.ruleset.value},
        )
    )
    logger.info("Game reset to demo scenario using ruleset={}", payload.ruleset.value)
    return to_game_state_payload(state)


@router.get("/rulesets", response_model=RulesetsPayload)
async def rulesets() -> RulesetsPayload:
    """Return supported rulesets that can be selected for a new game."""

    return RulesetsPayload(rulesets=list(available_rulesets()))


@router.get("/state", response_model=GameStatePayload)
async def game_state(store: GameStateStore = Depends(get_game_store)) -> GameStatePayload:
    """Return current in-memory game state."""

    return to_game_state_payload(store.state)


@router.get("/legal-moves/{unit_id}", response_model=LegalMovesPayload)
async def legal_moves(unit_id: str, store: GameStateStore = Depends(get_game_store)) -> LegalMovesPayload:
    """Return legal move destinations and path preview metadata for one unit."""

    options = list_legal_move_options(store.state, unit_id)
    return to_legal_moves_payload(unit_id=unit_id, options=options)


@router.post("/phase", response_model=GameStatePayload)
async def set_phase(
    payload: SetPhasePayload,
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
) -> GameStatePayload:
    """Set minimal in-memory phase marker for development actions."""

    state = store.state.with_turn_phase(payload.phase)
    store.replace(state)
    event_stream.publish(
        _build_game_event(
            event_type="phase_changed",
            ok=True,
            reason="ok",
            details={"phase": payload.phase.value},
        )
    )
    logger.debug("Phase set to {}", payload.phase.value)
    return to_game_state_payload(state)


@router.websocket("/ws/events")
async def game_events(websocket: WebSocket, event_stream: GameEventStream = Depends(get_event_stream)) -> None:
    """Stream live action events for frontend event log updates."""

    await websocket.accept()
    subscriber_queue = event_stream.subscribe()
    try:
        while True:
            try:
                event = await asyncio.to_thread(subscriber_queue.get, True, 1.0)
            except Empty:
                continue

            await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        logger.debug("Game events websocket disconnected")
    finally:
        event_stream.unsubscribe(subscriber_queue)


@router.post("/action", response_model=ActionResponsePayload)
async def game_action(
    payload: MoveActionPayload,
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
) -> ActionResponsePayload:
    """Apply movement action and return updated state payload."""

    action = MoveAction(unit_id=payload.unit_id, destination=HexCoord(payload.destination.q, payload.destination.r))
    result = resolve_move(store.state, action)
    if result.ok:
        store.replace(result.state)
        logger.debug("Move resolved: unit={} destination=({}, {})", payload.unit_id, payload.destination.q, payload.destination.r)
    else:
        logger.debug("Move rejected: unit={} reason={}", payload.unit_id, result.reason)

    event_stream.publish(
        _build_game_event(
            event_type="move_resolved",
            ok=result.ok,
            reason=result.reason,
            details={
                "unit_id": payload.unit_id,
                "destination_q": payload.destination.q,
                "destination_r": payload.destination.r,
            },
        )
    )

    return to_action_response_payload(result)


@router.post("/action/missile", response_model=ActionResponsePayload)
async def missile_action(
    payload: MissileActionPayload,
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
) -> ActionResponsePayload:
    """Apply missile action and return updated state payload."""

    action = MissileAction(
        firing_unit_id=payload.firing_unit_id,
        target_unit_id=payload.target_unit_id,
        modifier_ids=tuple(payload.modifier_ids),
        fire_mode=payload.fire_mode,
        reaction_trigger=payload.reaction_trigger,
    )
    result = resolve_missile(store.state, action)
    if result.ok:
        store.replace(result.state)
        logger.debug(
            "Missile resolved: firing_unit={} target_unit={} modifiers={}",
            payload.firing_unit_id,
            payload.target_unit_id,
            payload.modifier_ids,
        )
    else:
        logger.debug(
            "Missile rejected: firing_unit={} target_unit={} reason={}",
            payload.firing_unit_id,
            payload.target_unit_id,
            result.reason,
        )

    event_stream.publish(
        _build_game_event(
            event_type="missile_resolved",
            ok=result.ok,
            reason=result.reason,
            details={
                "firing_unit_id": payload.firing_unit_id,
                "target_unit_id": payload.target_unit_id,
                "fire_mode": payload.fire_mode,
            },
        )
    )

    return to_action_response_payload(result)


@router.post("/preview/missile", response_model=MissilePreviewResponsePayload)
async def missile_preview(
    payload: MissileActionPayload,
    store: GameStateStore = Depends(get_game_store),
) -> MissilePreviewResponsePayload:
    """Return read-only missile preview details without mutating game state."""

    action = MissileAction(
        firing_unit_id=payload.firing_unit_id,
        target_unit_id=payload.target_unit_id,
        modifier_ids=tuple(payload.modifier_ids),
        fire_mode=payload.fire_mode,
        reaction_trigger=payload.reaction_trigger,
    )
    preview, reason = preview_missile(store.state, action)
    return to_missile_preview_response_payload(preview=preview, reason=reason)


@router.post("/action/missile/reload", response_model=ActionResponsePayload)
async def missile_reload_action(
    payload: MissileReloadActionPayload,
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
) -> ActionResponsePayload:
    """Apply missile reload action and return updated state payload."""

    action = ReloadMissileAction(unit_id=payload.unit_id)
    result = resolve_reload(store.state, action)
    if result.ok:
        store.replace(result.state)
        logger.debug("Missile reload resolved: unit={}", payload.unit_id)
    else:
        logger.debug("Missile reload rejected: unit={} reason={}", payload.unit_id, result.reason)

    event_stream.publish(
        _build_game_event(
            event_type="reload_resolved",
            ok=result.ok,
            reason=result.reason,
            details={"unit_id": payload.unit_id},
        )
    )

    return to_action_response_payload(result)


@router.post("/action/shock", response_model=ActionResponsePayload)
async def shock_action(
    payload: ShockActionPayload,
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
) -> ActionResponsePayload:
    """Apply shock action and return updated state payload."""

    action = ShockAction(
        attacker_unit_id=payload.attacker_unit_id,
        defender_unit_id=payload.defender_unit_id,
        angle=payload.angle,
        modifier_ids=tuple(payload.modifier_ids),
    )
    result = resolve_shock(store.state, action)
    if result.ok:
        store.replace(result.state)
        logger.debug(
            "Shock resolved: attacker={} defender={} angle={} modifiers={}",
            payload.attacker_unit_id,
            payload.defender_unit_id,
            payload.angle,
            payload.modifier_ids,
        )
    else:
        logger.debug(
            "Shock rejected: attacker={} defender={} reason={}",
            payload.attacker_unit_id,
            payload.defender_unit_id,
            result.reason,
        )

    event_stream.publish(
        _build_game_event(
            event_type="shock_resolved",
            ok=result.ok,
            reason=result.reason,
            details={
                "attacker_unit_id": payload.attacker_unit_id,
                "defender_unit_id": payload.defender_unit_id,
                "angle": payload.angle,
            },
        )
    )

    return to_action_response_payload(result)


@router.post("/preview/shock", response_model=ShockPreviewResponsePayload)
async def shock_preview(
    payload: ShockActionPayload,
    store: GameStateStore = Depends(get_game_store),
) -> ShockPreviewResponsePayload:
    """Return read-only shock preview details without mutating game state."""

    action = ShockAction(
        attacker_unit_id=payload.attacker_unit_id,
        defender_unit_id=payload.defender_unit_id,
        angle=payload.angle,
        modifier_ids=tuple(payload.modifier_ids),
    )
    preview, reason = preview_shock(store.state, action)
    return to_shock_preview_response_payload(preview=preview, reason=reason)


def _build_game_event(
    event_type: GameEventType,
    ok: bool | None,
    reason: str | None,
    details: dict[str, str | int | bool | None],
) -> GameEventPayload:
    """Create one websocket event payload with deterministic transport shape."""

    return GameEventPayload(
        event_id=str(uuid4()),
        timestamp=datetime.now(tz=UTC).isoformat(),
        event_type=event_type,
        ok=ok,
        reason=reason,
        details=details,
    )
