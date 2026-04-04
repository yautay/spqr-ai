"""Game state and action routes."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from loguru import logger

from legions_api.api.dependencies import get_game_store
from legions_api.api.mapper import to_action_response_payload, to_game_state_payload
from legions_api.api.schemas import (
    ActionResponsePayload,
    GameStatePayload,
    MissileActionPayload,
    MoveActionPayload,
    NewGamePayload,
    RulesetsPayload,
)
from legions_api.api.state_store import GameStateStore
from legions_api.core.actions import MissileAction, MoveAction
from legions_api.core.model.hex import HexCoord
from legions_api.core.rules.missile import resolve_missile
from legions_api.core.rules.movement import resolve_move
from legions_api.core.tables.loader import available_rulesets

router = APIRouter(prefix="/game", tags=["game"])


@router.post("/new", response_model=GameStatePayload)
async def new_game(
    payload: NewGamePayload = Body(default_factory=NewGamePayload),
    store: GameStateStore = Depends(get_game_store),
) -> GameStatePayload:
    """Reset in-memory game and return the fresh state."""

    state = store.reset(ruleset_mode=payload.ruleset)
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


@router.post("/action", response_model=ActionResponsePayload)
async def game_action(
    payload: MoveActionPayload,
    store: GameStateStore = Depends(get_game_store),
) -> ActionResponsePayload:
    """Apply movement action and return updated state payload."""

    action = MoveAction(unit_id=payload.unit_id, destination=HexCoord(payload.destination.q, payload.destination.r))
    result = resolve_move(store.state, action)
    if result.ok:
        store.replace(result.state)
        logger.debug("Move resolved: unit={} destination=({}, {})", payload.unit_id, payload.destination.q, payload.destination.r)
    else:
        logger.debug("Move rejected: unit={} reason={}", payload.unit_id, result.reason)

    return to_action_response_payload(result)


@router.post("/action/missile", response_model=ActionResponsePayload)
async def missile_action(
    payload: MissileActionPayload,
    store: GameStateStore = Depends(get_game_store),
) -> ActionResponsePayload:
    """Apply missile action and return updated state payload."""

    action = MissileAction(
        firing_unit_id=payload.firing_unit_id,
        target_unit_id=payload.target_unit_id,
        modifier_ids=tuple(payload.modifier_ids),
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

    return to_action_response_payload(result)
