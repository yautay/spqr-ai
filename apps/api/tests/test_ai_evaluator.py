"""Tests for AI heuristic evaluator."""

from legions_api.ai.evaluator import evaluate_state
from legions_api.core.bootstrap import create_demo_state
from legions_api.core.model.unit import Side


def test_evaluator_rewards_enemy_damage_from_perspective() -> None:
    """Position score should improve when enemy accumulates cohesion hits."""

    state = create_demo_state()
    baseline = evaluate_state(state, perspective=Side.RED)

    updated_units = dict(state.units)
    updated_units["b1"] = updated_units["b1"].with_added_cohesion_hits(2)
    damaged_enemy_state = state.with_units(updated_units)

    improved = evaluate_state(damaged_enemy_state, perspective=Side.RED)

    assert improved > baseline


def test_evaluator_penalizes_routed_friendly_units() -> None:
    """Position score should drop when friendly unit becomes routed."""

    state = create_demo_state()
    baseline = evaluate_state(state, perspective=Side.RED)

    updated_units = dict(state.units)
    updated_units["r1"] = updated_units["r1"].with_routed(True)
    routed_state = state.with_units(updated_units)

    degraded = evaluate_state(routed_state, perspective=Side.RED)

    assert degraded < baseline
