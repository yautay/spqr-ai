"""Deterministic heuristic evaluator for AI search."""

from __future__ import annotations

from legions_api.core.model.game_state import GameState
from legions_api.core.model.unit import Side
from legions_api.core.rules.facing import wide_frontage_anchor


def evaluate_state(state: GameState, perspective: Side) -> float:
    """Return deterministic board score where larger is better for perspective side."""

    score = 0.0
    own_units = [unit for unit in state.units.values() if unit.side == perspective]
    enemy_units = [unit for unit in state.units.values() if unit.side != perspective]

    for unit in own_units:
        score += 100.0
        score -= 6.0 * unit.cohesion_hits
        if unit.is_routed:
            score -= 30.0

    for unit in enemy_units:
        score -= 100.0
        score += 6.0 * unit.cohesion_hits
        if unit.is_routed:
            score += 30.0

    score += _formation_pressure_bonus(own_units=own_units, enemy_units=enemy_units)
    return score


def _formation_pressure_bonus(own_units, enemy_units) -> float:
    """Reward states where perspective units are closer to enemy line."""

    if not own_units or not enemy_units:
        return 0.0

    total_distance = 0
    for unit in own_units:
        unit_anchor = wide_frontage_anchor(unit)
        nearest_enemy_distance = min(unit_anchor.distance_to(wide_frontage_anchor(enemy)) for enemy in enemy_units)
        total_distance += nearest_enemy_distance

    average_distance = total_distance / len(own_units)
    return max(0.0, 10.0 - average_distance)
