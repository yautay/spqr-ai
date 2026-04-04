"""Cross-module reaction and reload flow regression test."""

from __future__ import annotations

from legions_api.core.actions import MissileAction, MoveAction, ReloadMissileAction
from legions_api.core.model.game_state import GameState, TurnPhase
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import Side, Unit
from legions_api.core.rules.missile import resolve_missile, resolve_reload
from legions_api.core.rules.movement import resolve_move
from legions_api.core.tables.loader import load_ruleset


def test_move_reaction_and_reload_flow() -> None:
    """Movement should open reaction window, reaction should spend it, reload should work in reload phase."""

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
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(3, 0), missile_class_id="J"),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
        rng_seed=10,
    )

    moved = resolve_move(state, MoveAction(unit_id="r1", destination=HexCoord(1, 0)))
    assert moved.ok
    assert [event.event_type for event in moved.events] == ["reaction_window_opened"]

    reaction = resolve_missile(
        moved.state,
        MissileAction(
            firing_unit_id="b1",
            target_unit_id="r1",
            fire_mode="reaction",
            reaction_trigger="entry",
        ),
    )
    assert reaction.ok
    assert [event.event_type for event in reaction.events] == [
        "missile_fired",
        "reaction_fire",
        "supply_changed",
        "reaction_window_spent",
    ]

    repeat_reaction = resolve_missile(
        reaction.state,
        MissileAction(
            firing_unit_id="b1",
            target_unit_id="r1",
            fire_mode="reaction",
            reaction_trigger="entry",
        ),
    )
    assert not repeat_reaction.ok
    assert repeat_reaction.reason == "reaction_window_spent"

    reload_state = reaction.state.with_turn_phase(TurnPhase.ROUT_AND_RELOAD).with_active_side(Side.BLUE)
    reload = resolve_reload(reload_state, ReloadMissileAction(unit_id="b1"))
    assert reload.ok
    assert [event.event_type for event in reload.events] == ["reload_attempt", "supply_changed"]
