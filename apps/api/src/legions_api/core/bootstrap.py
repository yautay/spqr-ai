"""Create baseline game states for development."""

from __future__ import annotations

from legions_api.core.model.game_state import GameState
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.scenario.loader import load_scenario_state


def create_demo_state(mode: RulesetMode = RulesetMode.ORIGINAL, scenario_id: str = "demo") -> GameState:
    """Return deterministic state loaded from scenario assets."""

    return load_scenario_state(scenario_id=scenario_id, mode=mode)
