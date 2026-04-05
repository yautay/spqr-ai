"""FastAPI dependency providers."""

from __future__ import annotations

from legions_api.api.event_stream import GameEventStream
from legions_api.api.state_store import GameStateStore

_STORE = GameStateStore()
_EVENT_STREAM = GameEventStream()


def get_game_store() -> GameStateStore:
    """Return singleton in-memory state store for early development."""

    return _STORE


def get_event_stream() -> GameEventStream:
    """Return singleton in-memory event stream."""

    return _EVENT_STREAM
