"""Action validation and resolution result models."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.game_state import GameState


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Outcome of attempting to resolve an action."""

    ok: bool
    reason: str
    state: GameState
