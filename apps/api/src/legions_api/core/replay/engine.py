"""Deterministic replay from persisted replay events."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, cast

from legions_api.core.actions import MissileAction, MoveAction, ReloadMissileAction, ShockAction
from legions_api.core.bootstrap import create_demo_state
from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.rules.missile import resolve_missile, resolve_reload
from legions_api.core.rules.movement import resolve_move
from legions_api.core.rules.shock import resolve_shock
from legions_api.core.turn import advance_activation_step, end_turn
from legions_api.persistence.replay_log import ReplayEvent
from legions_api.persistence.state_codec import encode_state


@dataclass(frozen=True, slots=True)
class ReplayVerification:
    """Replay verification result against current state snapshot."""

    ok: bool
    reason: str
    replay_state_hash: str
    current_state_hash: str
    total_events: int


def replay_events(events: tuple[ReplayEvent, ...]) -> GameState:
    """Replay ordered events and reconstruct final deterministic state."""

    state = create_demo_state()
    for replay_event in events:
        state = _apply_event(state, replay_event)
    return state


def verify_replay_state(current_state: GameState, events: tuple[ReplayEvent, ...]) -> ReplayVerification:
    """Verify replay reconstruction hash matches current runtime state."""

    replay_state = replay_events(events)
    replay_hash = _state_hash(replay_state)
    current_hash = _state_hash(current_state)
    if replay_hash == current_hash:
        return ReplayVerification(
            ok=True,
            reason="ok",
            replay_state_hash=replay_hash,
            current_state_hash=current_hash,
            total_events=len(events),
        )

    return ReplayVerification(
        ok=False,
        reason="state_mismatch",
        replay_state_hash=replay_hash,
        current_state_hash=current_hash,
        total_events=len(events),
    )


def _apply_event(state: GameState, replay_event: ReplayEvent) -> GameState:
    """Apply one replay event to state."""

    payload = replay_event.payload
    if replay_event.event_type == "game_reset":
        ruleset_value = payload.get("ruleset", RulesetMode.ORIGINAL.value)
        scenario_id = str(payload.get("scenario_id", "demo"))
        return create_demo_state(mode=RulesetMode(str(ruleset_value)), scenario_id=scenario_id)

    if replay_event.event_type == "activation_advanced":
        next_state, _ = advance_activation_step(state)
        return next_state

    if replay_event.event_type == "turn_ended":
        next_state, _ = end_turn(state)
        return next_state

    if replay_event.event_type == "move_resolved":
        move_action = MoveAction(
            unit_id=str(payload["unit_id"]),
            destination=HexCoord(q=_as_int(payload["destination_q"]), r=_as_int(payload["destination_r"])),
        )
        result = resolve_move(state, move_action)
        return result.state

    if replay_event.event_type == "missile_resolved":
        missile_action = MissileAction(
            firing_unit_id=str(payload["firing_unit_id"]),
            target_unit_id=str(payload["target_unit_id"]),
            modifier_ids=tuple(str(value) for value in _as_list(payload.get("modifier_ids", []))),
            fire_mode=_as_fire_mode(payload.get("fire_mode", "active")),
            reaction_trigger=_as_reaction_trigger(payload.get("reaction_trigger")),
        )
        result = resolve_missile(state, missile_action)
        return result.state

    if replay_event.event_type == "reload_resolved":
        result = resolve_reload(state, ReloadMissileAction(unit_id=str(payload["unit_id"])))
        return result.state

    if replay_event.event_type == "shock_resolved":
        shock_action = ShockAction(
            attacker_unit_id=str(payload["attacker_unit_id"]),
            defender_unit_id=str(payload["defender_unit_id"]),
            angle=_as_shock_angle(payload.get("angle", "front")),
            modifier_ids=tuple(str(value) for value in _as_list(payload.get("modifier_ids", []))),
        )
        result = resolve_shock(state, shock_action)
        return result.state

    return state


def _state_hash(state: GameState) -> str:
    """Return stable hash for serialized game state snapshot."""

    payload = encode_state(state)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _as_list(value: object) -> list[object]:
    """Cast object to list with safe fallback."""

    if isinstance(value, list):
        return value
    return []


def _as_int(value: object) -> int:
    """Convert replay payload field to integer."""

    if isinstance(value, bool):
        raise ValueError("expected integer payload")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError("expected integer payload")


def _as_fire_mode(value: object) -> Literal["active", "reaction"]:
    """Convert replay payload field to missile fire mode literal."""

    normalized = str(value)
    if normalized not in {"active", "reaction"}:
        raise ValueError("unknown fire mode")
    return cast(Literal["active", "reaction"], normalized)


def _as_reaction_trigger(value: object) -> Literal["entry", "retire", "return"] | None:
    """Convert replay payload field to optional reaction trigger literal."""

    if value is None:
        return None
    normalized = str(value)
    if normalized not in {"entry", "retire", "return"}:
        raise ValueError("unknown reaction trigger")
    return cast(Literal["entry", "retire", "return"], normalized)


def _as_shock_angle(value: object) -> Literal["front", "flank", "rear"]:
    """Convert replay payload field to shock angle literal."""

    normalized = str(value)
    if normalized not in {"front", "flank", "rear"}:
        raise ValueError("unknown shock angle")
    return cast(Literal["front", "flank", "rear"], normalized)
