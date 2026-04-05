"""In-memory state store for early development."""

from __future__ import annotations

from legions_api.core.bootstrap import create_demo_state
from legions_api.core.model.game_state import GameState
from legions_api.core.model.ruleset import RulesetMode


class GameStateStore:
    """Simple mutable holder for one game instance."""

    def __init__(self) -> None:
        self._state = create_demo_state()

    @property
    def state(self) -> GameState:
        """Return current game state."""

        return self._state

    def reset(self, ruleset_mode: RulesetMode = RulesetMode.ORIGINAL, scenario_id: str = "demo") -> GameState:
        """Reset game to deterministic demo state."""

        self._state = create_demo_state(mode=ruleset_mode, scenario_id=scenario_id)
        return self._state

    def replace(self, state: GameState) -> None:
        """Replace current state with provided immutable snapshot."""

        self._state = state
