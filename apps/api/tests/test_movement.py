"""Movement rule tests."""

import pytest

from legions_api.core.actions import MoveAction
from legions_api.core.model.game_state import GameState
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, TerrainType, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import Side, Unit
from legions_api.core.rules import movement as movement_rules
from legions_api.core.rules.movement import resolve_move
from legions_api.core.tables.loader import load_ruleset
from legions_api.core.tables.models import StackingVoluntaryTableModel


def test_move_fails_when_unit_starts_in_enemy_zoc() -> None:
    """Units cannot move while pinned by adjacent enemy ZOC."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert not result.ok
    assert result.reason == "unit_pinned_by_enemy_zoc"


def test_move_rejects_no_op_before_destination_occupied_check() -> None:
    """Moving to the same hex should return no-op reason."""

    scenario_map = build_irregular_map(tiles=[HexTile(coord=HexCoord(0, 0))])
    units = {"r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1)}
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 0)))

    assert not result.ok
    assert result.reason == "no_op_move"


def test_move_succeeds_when_path_cost_within_allowance() -> None:
    """Movement resolves through pathfinding within move allowance."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(0, 1)),
            HexTile(coord=HexCoord(1, 1)),
        ]
    )
    units = {"r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=2)}
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(1, 1)))

    assert result.ok
    assert result.state.units["r1"].position == HexCoord(1, 1)


def test_simple_ruleset_does_not_lock_movement_in_enemy_zoc() -> None:
    """Simple ruleset allows movement from enemy ZOC for faster play."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.SIMPLE),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert result.ok


def test_move_uses_unit_specific_movement_profile_when_set() -> None:
    """Unit movement profile should override ruleset default terrain costs."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0), terrain=TerrainType.CLEAR),
            HexTile(coord=HexCoord(1, 0), terrain=TerrainType.ROUGH),
        ]
    )
    units = {
        "r1": Unit(
            unit_id="r1",
            side=Side.RED,
            position=HexCoord(0, 0),
            move_allowance=1,
            move_profile_id="simple_standard",
        )
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(1, 0)))

    assert result.ok


def test_move_fails_when_intermediate_occupied_and_stacking_disallows_pass_through() -> None:
    """Movement fails when only path crosses occupied hex and table disallows pass-through."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
            HexTile(coord=HexCoord(0, 2)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=2),
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 2)))

    assert not result.ok
    assert result.reason == "no_valid_path"


def test_move_can_pass_through_occupied_hex_when_stacking_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Movement can cross occupied hex when stacking row allows moving category pair."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
            HexTile(coord=HexCoord(0, 2)),
        ]
    )
    units = {
        "r1": Unit(
            unit_id="r1",
            side=Side.RED,
            position=HexCoord(0, 0),
            move_allowance=2,
            stacking_category="scout",
        ),
        "r2": Unit(
            unit_id="r2",
            side=Side.RED,
            position=HexCoord(0, 1),
            move_allowance=1,
            stacking_category="basic",
        ),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    custom_stacking_table = StackingVoluntaryTableModel.model_validate(
        {
            "table_id": "stacking_voluntary",
            "version": "test",
            "rows": [
                {
                    "moving_category": "scout",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": False,
                    "moving_unit_cohesion_hits": None,
                    "stationary_unit_cohesion_hits": None,
                    "tq_check_drm": None,
                }
            ],
        }
    )

    monkeypatch.setattr(movement_rules, "load_table", lambda table_id: custom_stacking_table)

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 2)))

    assert result.ok


def test_move_can_stop_in_occupied_hex_when_stacking_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Destination stacking stop should succeed when table allows moving/stationary category pair."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1, stacking_category="scout"),
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1, stacking_category="basic"),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    custom_stacking_table = StackingVoluntaryTableModel.model_validate(
        {
            "table_id": "stacking_voluntary",
            "version": "test",
            "rows": [
                {
                    "moving_category": "scout",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": True,
                    "moving_unit_cohesion_hits": 0,
                    "stationary_unit_cohesion_hits": 0,
                    "tq_check_drm": 0,
                }
            ],
        }
    )

    monkeypatch.setattr(movement_rules, "load_table", lambda table_id: custom_stacking_table)

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert result.ok
    assert result.state.units["r1"].position == HexCoord(0, 1)
    assert set(result.state.occupant_by_hex[HexCoord(0, 1)]) == {"r1", "r2"}


def test_move_through_fails_when_any_occupant_category_disallows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass-through should fail when occupied hex has mixed categories and one row disallows."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
            HexTile(coord=HexCoord(0, 2)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=2, stacking_category="scout"),
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1, stacking_category="basic"),
        "r3": Unit(unit_id="r3", side=Side.RED, position=HexCoord(0, 1), move_allowance=1, stacking_category="heavy"),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    custom_stacking_table = StackingVoluntaryTableModel.model_validate(
        {
            "table_id": "stacking_voluntary",
            "version": "test",
            "rows": [
                {
                    "moving_category": "scout",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": False,
                    "moving_unit_cohesion_hits": None,
                    "stationary_unit_cohesion_hits": None,
                    "tq_check_drm": None,
                }
            ],
        }
    )

    monkeypatch.setattr(movement_rules, "load_table", lambda table_id: custom_stacking_table)

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 2)))

    assert not result.ok
    assert result.reason == "no_valid_path"


def test_move_applies_cohesion_hits_on_pass_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pass-through interactions should apply cohesion side effects and expose metadata."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
            HexTile(coord=HexCoord(0, 2)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=2, stacking_category="scout"),
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1, stacking_category="basic"),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    custom_stacking_table = StackingVoluntaryTableModel.model_validate(
        {
            "table_id": "stacking_voluntary",
            "version": "test",
            "rows": [
                {
                    "moving_category": "scout",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": False,
                    "moving_unit_cohesion_hits": 1,
                    "stationary_unit_cohesion_hits": 2,
                    "tq_check_drm": -1,
                }
            ],
        }
    )

    monkeypatch.setattr(movement_rules, "load_table", lambda table_id: custom_stacking_table)

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 2)))

    assert result.ok
    assert result.state.units["r1"].cohesion_hits == 1
    assert result.state.units["r2"].cohesion_hits == 2
    assert len(result.effects) == 1
    assert result.effects[0].interaction == "pass_through"
    assert result.effects[0].location == HexCoord(0, 1)
    assert result.effects[0].moving_unit_cohesion_hits == 1
    assert result.effects[0].stationary_unit_cohesion_hits == 2
    assert result.effects[0].tq_check_drm == -1
    assert len(result.pending_tq_checks) == 1
    assert result.pending_tq_checks[0].unit_id == "r2"
    assert result.pending_tq_checks[0].drm == -1


def test_move_applies_cohesion_hits_on_stop_in_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop-in-hex stacking interactions should apply cohesion side effects."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1, stacking_category="scout"),
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1, stacking_category="basic"),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    custom_stacking_table = StackingVoluntaryTableModel.model_validate(
        {
            "table_id": "stacking_voluntary",
            "version": "test",
            "rows": [
                {
                    "moving_category": "scout",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": True,
                    "moving_unit_cohesion_hits": 2,
                    "stationary_unit_cohesion_hits": 1,
                    "tq_check_drm": 0,
                }
            ],
        }
    )

    monkeypatch.setattr(movement_rules, "load_table", lambda table_id: custom_stacking_table)

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert result.ok
    assert result.state.units["r1"].cohesion_hits == 2
    assert result.state.units["r2"].cohesion_hits == 1
    assert len(result.effects) == 1
    assert result.effects[0].interaction == "stop_in_hex"
    assert result.effects[0].location == HexCoord(0, 1)
    assert len(result.pending_tq_checks) == 1
    assert result.pending_tq_checks[0].unit_id == "r2"
    assert result.pending_tq_checks[0].drm == 0
