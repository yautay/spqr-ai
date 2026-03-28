"""FastAPI dependency providers."""

from __future__ import annotations

from legions_api.api.state_store import GameStateStore

_STORE = GameStateStore()


def get_game_store() -> GameStateStore:
    """Return singleton in-memory state store for early development."""

    return _STORE
