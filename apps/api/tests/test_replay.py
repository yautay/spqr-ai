"""Deterministic replay reconstruction tests."""

from __future__ import annotations

from legions_api.core.actions import MoveAction, ShockAction
from legions_api.core.model.hex import HexCoord
from legions_api.core.replay import replay_events, verify_replay_state
from legions_api.core.rules.movement import resolve_move
from legions_api.core.rules.shock import resolve_shock
from legions_api.core.turn import advance_activation_step
from legions_api.persistence.replay_log import ReplayEvent


def test_replay_events_is_deterministic_for_fixed_sequence() -> None:
    """Replaying same event stream twice should produce equal state hashes."""

    events = (
        ReplayEvent(event_type="game_reset", payload={"ruleset": "original", "scenario_id": "demo"}),
        ReplayEvent(event_type="move_resolved", payload={"unit_id": "r1", "destination_q": 1, "destination_r": 0}),
        ReplayEvent(event_type="activation_advanced", payload={}),
        ReplayEvent(
            event_type="shock_resolved",
            payload={
                "attacker_unit_id": "r1",
                "defender_unit_id": "b1",
                "angle": "front",
                "modifier_ids": [],
            },
        ),
    )

    first = replay_events(events)
    second = replay_events(events)

    assert first == second


def test_verify_replay_state_matches_live_resolution_for_fixed_sequence() -> None:
    """Replay verification should pass for known deterministic event stream."""

    events = (
        ReplayEvent(event_type="game_reset", payload={"ruleset": "original", "scenario_id": "demo"}),
        ReplayEvent(event_type="move_resolved", payload={"unit_id": "r1", "destination_q": 1, "destination_r": 0}),
        ReplayEvent(event_type="activation_advanced", payload={}),
        ReplayEvent(
            event_type="shock_resolved",
            payload={
                "attacker_unit_id": "r1",
                "defender_unit_id": "b1",
                "angle": "front",
                "modifier_ids": [],
            },
        ),
    )

    state = replay_events((events[0],))
    state = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(1, 0))).state
    state, _ = advance_activation_step(state)
    state = resolve_shock(state, ShockAction(attacker_unit_id="r1", defender_unit_id="b1", angle="front")).state

    verification = verify_replay_state(state, events)

    assert verification.ok
    assert verification.reason == "ok"
    assert verification.total_events == len(events)
