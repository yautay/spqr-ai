"""Missile rule tests."""

from __future__ import annotations

import pytest

from legions_api.core.actions import MissileAction
from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import Side, Unit
from legions_api.core.rules import missile as missile_rules
from legions_api.core.rules.missile import resolve_missile
from legions_api.core.tables.loader import load_ruleset
from legions_api.core.tables.models import MissileTableModel


def test_missile_hit_applies_cohesion_and_advances_rng(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful missile hit should add one cohesion hit and advance RNG counter."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=7))

    result = resolve_missile(state, MissileAction(firing_unit_id="r1", target_unit_id="b1"))

    assert result.ok
    assert result.reason == "ok"
    assert result.state.units["b1"].cohesion_hits == 1
    assert result.state.rng_counter == 1
    assert result.missile_outcome is not None
    assert result.missile_outcome.base_roll == 6
    assert result.missile_outcome.hit
    assert result.missile_outcome.applied_cohesion_hits == 1


def test_missile_miss_does_not_change_target_cohesion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missile miss should keep target cohesion unchanged."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=4))

    result = resolve_missile(state, MissileAction(firing_unit_id="r1", target_unit_id="b1"))

    assert result.ok
    assert result.state.units["b1"].cohesion_hits == 0
    assert result.state.rng_counter == 1
    assert result.missile_outcome is not None
    assert not result.missile_outcome.hit
    assert result.missile_outcome.applied_cohesion_hits == 0


def test_missile_rejects_target_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missile action should fail when no strength entry exists for computed range."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(2, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=7))

    result = resolve_missile(state, MissileAction(firing_unit_id="r1", target_unit_id="b1"))

    assert not result.ok
    assert result.reason == "target_out_of_range"
    assert result.state.rng_counter == 0


def _build_state(units: dict[str, Unit]) -> GameState:
    """Create a tiny deterministic battlefield for missile tests."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(2, 0)),
        ]
    )
    return GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )


def _missile_table(strength_at_range_one: int) -> MissileTableModel:
    """Build minimal missile table fixture for resolver tests."""

    return MissileTableModel.model_validate(
        {
            "table_id": "missile_range_results",
            "version": "test",
            "missile_classes": [
                {
                    "missile_class_id": "A",
                    "name": "archer",
                    "strength_by_range": {"1": strength_at_range_one},
                }
            ],
            "dr_modifiers": [],
        }
    )
