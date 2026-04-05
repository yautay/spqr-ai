"""Game state and action routes."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from queue import Empty
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, WebSocket, WebSocketDisconnect
from loguru import logger

from legions_api.api.dependencies import get_event_stream, get_game_store, get_replay_log, get_snapshot_repository
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
    LoadGamePayload,
    MissileActionPayload,
    MissilePreviewResponsePayload,
    MissileReloadActionPayload,
    MoveActionPayload,
    NewGamePayload,
    ReplayStatePayload,
    ReplayVerificationPayload,
    RulesetsPayload,
    SaveGamePayload,
    ScenariosPayload,
    ShockActionPayload,
    ShockPreviewResponsePayload,
    SnapshotListPayload,
    SnapshotPayload,
    SnapshotSummaryPayload,
)
from legions_api.api.state_store import GameStateStore
from legions_api.core.actions import MissileAction, MoveAction, ReloadMissileAction, ShockAction
from legions_api.core.model.hex import HexCoord
from legions_api.core.replay import replay_events, verify_replay_state
from legions_api.core.rules.missile import preview_missile, resolve_missile, resolve_reload
from legions_api.core.rules.movement import list_legal_move_options, resolve_move
from legions_api.core.rules.shock import preview_shock, resolve_shock
from legions_api.core.scenario.loader import available_scenarios
from legions_api.core.tables.loader import available_rulesets
from legions_api.core.turn import advance_activation_step, end_turn
from legions_api.persistence.replay_log import ReplayEvent, ReplayLog
from legions_api.persistence.snapshots import SnapshotRepository

router = APIRouter(prefix="/game", tags=["game"])

GameEventType = Literal[
    "game_reset",
    "game_saved",
    "game_loaded",
    "activation_advanced",
    "turn_ended",
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
    replay_log: ReplayLog = Depends(get_replay_log),
) -> GameStatePayload:
    """Reset in-memory game and return the fresh state."""

    event_stream.clear_history()
    replay_log.clear()
    state = store.reset(ruleset_mode=payload.ruleset, scenario_id=payload.scenario_id)
    replay_log.append(
        ReplayEvent(
            event_type="game_reset",
            payload={
                "ruleset": payload.ruleset.value,
                "scenario_id": payload.scenario_id,
            },
        )
    )
    event_stream.publish(
        _build_game_event(
            event_type="game_reset",
            ok=True,
            reason="ok",
            details={"ruleset": payload.ruleset.value, "scenario_id": payload.scenario_id},
        )
    )
    logger.info("Game reset to scenario={} using ruleset={}", payload.scenario_id, payload.ruleset.value)
    return to_game_state_payload(state)


@router.post("/save", response_model=SnapshotPayload)
async def save_game(
    payload: SaveGamePayload = Body(default_factory=SaveGamePayload),
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
    replay_log: ReplayLog = Depends(get_replay_log),
    snapshots: SnapshotRepository = Depends(get_snapshot_repository),
) -> SnapshotPayload:
    """Persist current game state snapshot under selected slot id."""

    record = snapshots.save(slot_id=payload.slot_id, state=store.state, event_offset=replay_log.total_events())
    event_stream.publish(
        _build_game_event(
            event_type="game_saved",
            ok=True,
            reason="ok",
            details={
                "slot_id": record.slot_id,
                "event_offset": record.event_offset,
            },
        )
    )
    return SnapshotPayload(
        slot_id=record.slot_id,
        saved_at=record.saved_at,
        event_offset=record.event_offset,
        state=to_game_state_payload(record.state),
    )


@router.post("/load", response_model=SnapshotPayload)
async def load_game(
    payload: LoadGamePayload = Body(default_factory=LoadGamePayload),
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
    snapshots: SnapshotRepository = Depends(get_snapshot_repository),
) -> SnapshotPayload:
    """Load previously saved snapshot into active game state."""

    record = snapshots.load(payload.slot_id)
    if record is None:
        return SnapshotPayload(
            slot_id=payload.slot_id,
            saved_at="",
            event_offset=0,
            state=to_game_state_payload(store.state),
        )

    store.replace(record.state)
    event_stream.publish(
        _build_game_event(
            event_type="game_loaded",
            ok=True,
            reason="ok",
            details={
                "slot_id": record.slot_id,
                "event_offset": record.event_offset,
            },
        )
    )
    return SnapshotPayload(
        slot_id=record.slot_id,
        saved_at=record.saved_at,
        event_offset=record.event_offset,
        state=to_game_state_payload(record.state),
    )


@router.get("/saves", response_model=SnapshotListPayload)
async def list_saves(snapshots: SnapshotRepository = Depends(get_snapshot_repository)) -> SnapshotListPayload:
    """List available snapshot slots."""

    return SnapshotListPayload(
        snapshots=[
            SnapshotSummaryPayload(
                slot_id=record.slot_id,
                saved_at=record.saved_at,
                event_offset=record.event_offset,
            )
            for record in snapshots.list_snapshots()
        ]
    )


@router.get("/replay", response_model=ReplayStatePayload)
async def replay_state_route(replay_log: ReplayLog = Depends(get_replay_log)) -> ReplayStatePayload:
    """Reconstruct current game state from ordered replay history."""

    events = replay_log.events()
    replay_state = replay_events(events)
    return ReplayStatePayload(total_events=len(events), state=to_game_state_payload(replay_state))


@router.get("/replay/verify", response_model=ReplayVerificationPayload)
async def replay_verify_route(
    store: GameStateStore = Depends(get_game_store),
    replay_log: ReplayLog = Depends(get_replay_log),
) -> ReplayVerificationPayload:
    """Verify replay reconstruction hash matches live state hash."""

    verification = verify_replay_state(store.state, replay_log.events())
    return ReplayVerificationPayload(
        ok=verification.ok,
        reason=verification.reason,
        total_events=verification.total_events,
        replay_state_hash=verification.replay_state_hash,
        current_state_hash=verification.current_state_hash,
    )


@router.get("/rulesets", response_model=RulesetsPayload)
async def rulesets() -> RulesetsPayload:
    """Return supported rulesets that can be selected for a new game."""

    return RulesetsPayload(rulesets=list(available_rulesets()))


@router.get("/scenarios", response_model=ScenariosPayload)
async def scenarios() -> ScenariosPayload:
    """Return scenario identifiers available for new game setup."""

    return ScenariosPayload(scenarios=list(available_scenarios()))


@router.get("/state", response_model=GameStatePayload)
async def game_state(store: GameStateStore = Depends(get_game_store)) -> GameStatePayload:
    """Return current in-memory game state."""

    return to_game_state_payload(store.state)


@router.get("/legal-moves/{unit_id}", response_model=LegalMovesPayload)
async def legal_moves(unit_id: str, store: GameStateStore = Depends(get_game_store)) -> LegalMovesPayload:
    """Return legal move destinations and path preview metadata for one unit."""

    options = list_legal_move_options(store.state, unit_id)
    return to_legal_moves_payload(unit_id=unit_id, options=options)


@router.post("/activation/advance", response_model=GameStatePayload)
async def advance_activation(
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
    replay_log: ReplayLog = Depends(get_replay_log),
) -> GameStatePayload:
    """Advance one activation step in deterministic turn sequence."""

    state, transition = advance_activation_step(store.state)
    store.replace(state)
    replay_log.append(ReplayEvent(event_type="activation_advanced", payload={}))
    event_stream.publish(
        _build_game_event(
            event_type="activation_advanced",
            ok=True,
            reason="ok",
            details={
                "from_phase": transition.previous_phase.value,
                "to_phase": transition.next_phase.value,
                "from_side": transition.previous_side.value,
                "to_side": transition.next_side.value,
                "from_turn": transition.previous_turn,
                "to_turn": transition.next_turn,
            },
        )
    )
    logger.debug(
        "Activation advanced: {} -> {} | side {} -> {} | turn {} -> {}",
        transition.previous_phase.value,
        transition.next_phase.value,
        transition.previous_side.value,
        transition.next_side.value,
        transition.previous_turn,
        transition.next_turn,
    )
    return to_game_state_payload(state)


@router.post("/end-turn", response_model=GameStatePayload)
async def force_end_turn(
    store: GameStateStore = Depends(get_game_store),
    event_stream: GameEventStream = Depends(get_event_stream),
    replay_log: ReplayLog = Depends(get_replay_log),
) -> GameStatePayload:
    """Force end current side and start opposite side orders segment."""

    state, transition = end_turn(store.state)
    store.replace(state)
    replay_log.append(ReplayEvent(event_type="turn_ended", payload={}))
    event_stream.publish(
        _build_game_event(
            event_type="turn_ended",
            ok=True,
            reason="ok",
            details={
                "from_phase": transition.previous_phase.value,
                "to_phase": transition.next_phase.value,
                "from_side": transition.previous_side.value,
                "to_side": transition.next_side.value,
                "from_turn": transition.previous_turn,
                "to_turn": transition.next_turn,
            },
        )
    )
    logger.debug(
        "Turn ended: phase {} -> {} | side {} -> {} | turn {} -> {}",
        transition.previous_phase.value,
        transition.next_phase.value,
        transition.previous_side.value,
        transition.next_side.value,
        transition.previous_turn,
        transition.next_turn,
    )
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
    replay_log: ReplayLog = Depends(get_replay_log),
) -> ActionResponsePayload:
    """Apply movement action and return updated state payload."""

    action = MoveAction(unit_id=payload.unit_id, destination=HexCoord(payload.destination.q, payload.destination.r))
    result = resolve_move(store.state, action)
    if result.ok:
        store.replace(result.state)
        replay_log.append(
            ReplayEvent(
                event_type="move_resolved",
                payload={
                    "unit_id": payload.unit_id,
                    "destination_q": payload.destination.q,
                    "destination_r": payload.destination.r,
                },
            )
        )
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
    replay_log: ReplayLog = Depends(get_replay_log),
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
        replay_log.append(
            ReplayEvent(
                event_type="missile_resolved",
                payload={
                    "firing_unit_id": payload.firing_unit_id,
                    "target_unit_id": payload.target_unit_id,
                    "modifier_ids": payload.modifier_ids,
                    "fire_mode": payload.fire_mode,
                    "reaction_trigger": payload.reaction_trigger,
                },
            )
        )
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
    replay_log: ReplayLog = Depends(get_replay_log),
) -> ActionResponsePayload:
    """Apply missile reload action and return updated state payload."""

    action = ReloadMissileAction(unit_id=payload.unit_id)
    result = resolve_reload(store.state, action)
    if result.ok:
        store.replace(result.state)
        replay_log.append(ReplayEvent(event_type="reload_resolved", payload={"unit_id": payload.unit_id}))
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
    replay_log: ReplayLog = Depends(get_replay_log),
) -> ActionResponsePayload:
    """Apply shock action and return updated state payload."""

    action = ShockAction(
        attacker_unit_id=payload.attacker_unit_id,
        defender_unit_id=payload.defender_unit_id,
        modifier_ids=tuple(payload.modifier_ids),
    )
    result = resolve_shock(store.state, action)
    if result.ok:
        store.replace(result.state)
        replay_log.append(
            ReplayEvent(
                event_type="shock_resolved",
                payload={
                    "attacker_unit_id": payload.attacker_unit_id,
                    "defender_unit_id": payload.defender_unit_id,
                    "modifier_ids": payload.modifier_ids,
                },
            )
        )
        logger.debug(
            "Shock resolved: attacker={} defender={} modifiers={}",
            payload.attacker_unit_id,
            payload.defender_unit_id,
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
                "angle": result.shock_outcome.angle if result.shock_outcome is not None else None,
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
