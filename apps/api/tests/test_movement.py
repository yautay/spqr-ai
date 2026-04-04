"""Movement rule tests."""

import pytest

from legions_api.core.actions import MoveAction
from legions_api.core.model.game_state import GameState, ReactionWindow
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, TerrainType, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import Side, Unit
from legions_api.core.random import seeded_d10_roll
from legions_api.core.results import PendingTQCheck
from legions_api.core.rules import movement as movement_rules
from legions_api.core.rules.movement import resolve_move
from legions_api.core.tables.loader import load_ruleset
from legions_api.core.tables.models import StackingMandatoryTableModel, StackingVoluntaryTableModel


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


def test_move_opens_reaction_window_event_on_entry_trigger() -> None:
    """Movement should expose reaction window event when target enters enemy missile range."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(2, 0)),
            HexTile(coord=HexCoord(3, 0)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(3, 0), move_allowance=1, missile_class_id="J"),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(1, 0)))

    assert result.ok
    assert [event.event_type for event in result.events] == ["reaction_window_opened"]
    assert result.events[0].unit_id == "b1"
    assert result.events[0].target_unit_id == "r1"
    assert result.events[0].reaction_trigger == "entry"
    assert result.state.open_reaction_windows == (
        ReactionWindow(firing_unit_id="b1", target_unit_id="r1", reaction_trigger="entry"),
    )


@pytest.mark.parametrize(
    ("previous_position", "current_position", "expected"),
    [
        (HexCoord(4, 0), HexCoord(2, 0), "entry"),
        (HexCoord(2, 0), HexCoord(4, 0), "retire"),
        (HexCoord(2, 1), HexCoord(2, 0), "return"),
        (HexCoord(4, 0), HexCoord(5, 0), None),
    ],
)
def test_resolve_reaction_trigger_detects_expected_window(
    previous_position: HexCoord,
    current_position: HexCoord,
    expected: str | None,
) -> None:
    """Reaction trigger helper should classify entry/retire/return transitions."""

    trigger = movement_rules._resolve_reaction_trigger(
        enemy_position=HexCoord(0, 0),
        previous_position=previous_position,
        current_position=current_position,
        max_range=3,
    )

    assert trigger == expected


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


def test_routed_enemy_unit_does_not_pin_with_zoc() -> None:
    """Routed enemy should not exert ZOC that pins movement."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), move_allowance=1, is_routed=True),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert result.ok


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
    assert result.pending_tq_checks[0].target == 6
    assert len(result.tq_check_outcomes) == 1
    assert result.tq_check_outcomes[0].unit_id == "r2"
    assert result.tq_check_outcomes[0].roll == 6
    assert result.tq_check_outcomes[0].passed
    assert not result.tq_check_outcomes[0].became_routed
    assert not result.state.units["r2"].is_routed
    assert result.state.rng_counter == 1


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
    assert result.pending_tq_checks[0].target == 7
    assert len(result.tq_check_outcomes) == 1
    assert result.tq_check_outcomes[0].unit_id == "r2"
    assert result.tq_check_outcomes[0].roll == 6
    assert result.tq_check_outcomes[0].passed
    assert not result.tq_check_outcomes[0].became_routed
    assert not result.state.units["r2"].is_routed
    assert result.state.rng_counter == 1


def test_parse_tq_formula_offset_supports_common_forms() -> None:
    """TQ formula parser should handle tq, tq+N and tq-N forms."""

    assert movement_rules._parse_tq_formula_offset(None) == 0
    assert movement_rules._parse_tq_formula_offset("tq") == 0
    assert movement_rules._parse_tq_formula_offset("tq+2") == 2
    assert movement_rules._parse_tq_formula_offset("tq-3") == -3


def test_parse_tq_formula_offset_rejects_unknown_form() -> None:
    """Unsupported formulas should fail fast for data quality."""

    with pytest.raises(ValueError, match="unsupported tq formula"):
        movement_rules._parse_tq_formula_offset("tq*2")


def test_resolve_pending_tq_checks_applies_cohesion_on_failed_roll() -> None:
    """Failed deterministic TQ checks should add cohesion hit to checked unit."""

    checks = (
        PendingTQCheck(
            unit_id="r2",
            location=HexCoord(0, 1),
            source="stacking",
            required=True,
            formula="tq-2",
            drm=0,
            target=5,
        ),
    )
    units = {
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1),
    }

    outcomes, next_counter = movement_rules._resolve_pending_tq_checks(
        checks,
        current_units=units,
        rng_seed=1,
        rng_counter=0,
    )

    assert len(outcomes) == 1
    assert outcomes[0].roll == 6
    assert not outcomes[0].passed
    assert outcomes[0].applied_cohesion_hits == 1
    assert outcomes[0].became_routed
    assert units["r2"].cohesion_hits == 1
    assert units["r2"].is_routed
    assert next_counter == 1


def test_seeded_d10_roll_is_deterministic_for_same_seed_and_counter() -> None:
    """Seeded roll helper should stay stable for identical RNG state."""

    first_roll = seeded_d10_roll(rng_seed=1, rng_counter=0)
    second_roll = seeded_d10_roll(rng_seed=1, rng_counter=0)

    assert first_roll == second_roll == 6


def test_seeded_d10_roll_changes_when_counter_advances() -> None:
    """Seeded roll helper should produce sequence as counter advances."""

    first_roll = seeded_d10_roll(rng_seed=1, rng_counter=0)
    second_roll = seeded_d10_roll(rng_seed=1, rng_counter=1)

    assert first_roll != second_roll


def test_failed_tq_check_does_not_re_route_already_routed_unit() -> None:
    """Repeated failed checks should keep routed state and report no new route transition."""

    checks = (
        PendingTQCheck(
            unit_id="r2",
            location=HexCoord(0, 1),
            source="stacking",
            required=True,
            formula="tq-2",
            drm=0,
            target=5,
        ),
    )
    units = {
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1, is_routed=True),
    }

    outcomes, _ = movement_rules._resolve_pending_tq_checks(
        checks,
        current_units=units,
        rng_seed=1,
        rng_counter=0,
    )

    assert len(outcomes) == 1
    assert not outcomes[0].passed
    assert not outcomes[0].became_routed
    assert units["r2"].is_routed


def test_routed_unit_uses_mandatory_stacking_for_pass_through() -> None:
    """Routed mover should use mandatory stacking chart instead of voluntary rules."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
            HexTile(coord=HexCoord(0, 2)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=2, is_routed=True),
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 2)))

    assert result.ok
    assert result.state.units["r1"].position == HexCoord(0, 2)


def test_routed_unit_cannot_stop_in_occupied_hex_when_mandatory_disallows() -> None:
    """Mandatory stacking stop constraint should block routed destination occupancy."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=1, is_routed=True),
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert not result.ok
    assert result.reason == "destination_occupied"


def test_routed_unit_can_emit_mandatory_tq_check(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mandatory stacking rows should produce pending and resolved TQ checks."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
            HexTile(coord=HexCoord(0, 2)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), move_allowance=2, is_routed=True),
        "r2": Unit(unit_id="r2", side=Side.RED, position=HexCoord(0, 1), move_allowance=1),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    custom_mandatory_table = StackingMandatoryTableModel.model_validate(
        {
            "table_id": "stacking_mandatory",
            "version": "test",
            "rows": [
                {
                    "moving_category": "routing_basic",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": False,
                    "moving_unit_cohesion_hits": None,
                    "stationary_unit_cohesion_hits": None,
                    "stationary_unit_tq_check": {
                        "required": True,
                        "formula": "tq-2",
                    },
                }
            ],
        }
    )

    original_load_table = movement_rules.load_table

    monkeypatch.setattr(
        movement_rules,
        "load_table",
        lambda table_id: custom_mandatory_table if table_id == "stacking_mandatory" else original_load_table(table_id),
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 2)))

    assert result.ok
    assert len(result.pending_tq_checks) == 1
    assert result.pending_tq_checks[0].formula == "tq-2"
    assert len(result.tq_check_outcomes) == 1
    assert result.tq_check_outcomes[0].roll == 6


def test_routed_move_rejects_unmapped_stacking_category() -> None:
    """Routed move should fail fast for categories missing mandatory map."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(0, 1)),
        ]
    )
    units = {
        "r1": Unit(
            unit_id="r1",
            side=Side.RED,
            position=HexCoord(0, 0),
            move_allowance=1,
            is_routed=True,
            stacking_category="unknown",
        ),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
    )

    result = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(0, 1)))

    assert not result.ok
    assert result.reason == "stacking_category_unmapped"
