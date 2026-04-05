"""Missile rule tests."""

from __future__ import annotations

import pytest

from legions_api.core.actions import MissileAction, ReloadMissileAction
from legions_api.core.model.game_state import GameState, ReactionWindow, TurnPhase
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, TerrainType, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.unit import MissileSupply, Side, Unit
from legions_api.core.rules import missile as missile_rules
from legions_api.core.rules.missile import resolve_missile, resolve_reload
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
    assert result.state.units["r1"].missile_supply == MissileSupply.LOW
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


def test_missile_rejects_invalid_active_reaction_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Active fire should reject reaction trigger payload values."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=8))

    result = resolve_missile(
        state,
        MissileAction(firing_unit_id="r1", target_unit_id="b1", fire_mode="active", reaction_trigger="entry"),
    )

    assert not result.ok
    assert result.reason == "invalid_reaction_trigger"


def test_reaction_fire_requires_trigger(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reaction fire should fail when trigger type is not provided."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=8))

    result = resolve_missile(
        state,
        MissileAction(firing_unit_id="r1", target_unit_id="b1", fire_mode="reaction"),
    )

    assert not result.ok
    assert result.reason == "missing_reaction_trigger"


def test_reaction_fire_rejects_missing_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reaction fire should fail when no movement-opened window is available."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        },
        active_side=Side.BLUE,
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=8))

    result = resolve_missile(
        state,
        MissileAction(
            firing_unit_id="r1",
            target_unit_id="b1",
            fire_mode="reaction",
            reaction_trigger="entry",
        ),
    )

    assert not result.ok
    assert result.reason == "reaction_window_unavailable"


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


def test_missile_rejects_when_line_of_sight_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missile action should fail when LOS is blocked by intermediate hex."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(2, 0)),
        },
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0), blocks_line_of_sight=True),
            HexTile(coord=HexCoord(2, 0)),
        ],
    )
    monkeypatch.setattr(
        missile_rules,
        "load_table",
        lambda table_id: _missile_table(strength_at_range_one=8, strength_at_range_two=8),
    )

    result = resolve_missile(state, MissileAction(firing_unit_id="r1", target_unit_id="b1"))

    assert not result.ok
    assert result.reason == "no_line_of_sight"
    assert result.state.rng_counter == 0


def test_missile_applies_drm_breakdown_and_modified_roll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured DR modifiers should shift roll and be exposed in breakdown order."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=6))

    result = resolve_missile(
        state,
        MissileAction(
            firing_unit_id="r1",
            target_unit_id="b1",
            modifier_ids=("target_woods", "target_sk"),
        ),
    )

    assert result.ok
    assert result.missile_outcome is not None
    assert result.missile_outcome.base_roll == 6
    assert result.missile_outcome.total_drm == 1
    assert result.missile_outcome.modified_roll == 7
    assert not result.missile_outcome.hit
    assert [entry.id for entry in result.missile_outcome.drm_breakdown] == ["target_woods", "target_sk"]
    assert [entry.drm for entry in result.missile_outcome.drm_breakdown] == [2, -1]


def test_missile_rejects_unknown_drm_modifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missile action should fail fast when modifier id is not in table data."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=8))

    result = resolve_missile(
        state,
        MissileAction(
            firing_unit_id="r1",
            target_unit_id="b1",
            modifier_ids=("unknown_modifier",),
        ),
    )

    assert not result.ok
    assert result.reason == "unknown_missile_drm"
    assert result.state.rng_counter == 0


def test_missile_auto_applies_terrain_modifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Target woods terrain should add configured DR modifier automatically."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        },
        tiles=[
            HexTile(coord=HexCoord(0, 0), terrain=TerrainType.CLEAR),
            HexTile(coord=HexCoord(1, 0), terrain=TerrainType.WOODS),
            HexTile(coord=HexCoord(2, 0), terrain=TerrainType.CLEAR),
        ],
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=7))

    result = resolve_missile(state, MissileAction(firing_unit_id="r1", target_unit_id="b1"))

    assert result.ok
    assert result.missile_outcome is not None
    assert result.missile_outcome.total_drm == 2
    assert [entry.id for entry in result.missile_outcome.drm_breakdown] == ["target_woods"]


def test_missile_auto_applies_depleted_supply_modifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Low missile supply should add depleted DR modifier automatically."""

    state = _build_state(
        units={
            "r1": Unit(
                unit_id="r1",
                side=Side.RED,
                position=HexCoord(0, 0),
                missile_class_id="A",
                missile_supply=MissileSupply.LOW,
            ),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=6))

    result = resolve_missile(state, MissileAction(firing_unit_id="r1", target_unit_id="b1"))

    assert result.ok
    assert result.missile_outcome is not None
    assert result.missile_outcome.total_drm == 1
    assert result.missile_outcome.modified_roll == 7
    assert [entry.id for entry in result.missile_outcome.drm_breakdown] == ["firing_unit_depleted"]


def test_missile_auto_modifiers_do_not_duplicate_explicit_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit modifier ids should not duplicate identical state-driven modifiers."""

    state = _build_state(
        units={
            "r1": Unit(
                unit_id="r1",
                side=Side.RED,
                position=HexCoord(0, 0),
                missile_class_id="A",
                missile_supply=MissileSupply.LOW,
            ),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=6))

    result = resolve_missile(
        state,
        MissileAction(
            firing_unit_id="r1",
            target_unit_id="b1",
            modifier_ids=("firing_unit_depleted",),
        ),
    )

    assert result.ok
    assert result.missile_outcome is not None
    assert result.missile_outcome.total_drm == 1
    assert [entry.id for entry in result.missile_outcome.drm_breakdown] == ["firing_unit_depleted"]


def test_reaction_fire_emits_reaction_and_supply_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reaction fire should emit reaction and supply transition events."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        },
        active_side=Side.BLUE,
        open_reaction_windows=(ReactionWindow(firing_unit_id="r1", target_unit_id="b1", reaction_trigger="entry"),),
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=8))

    result = resolve_missile(
        state,
        MissileAction(
            firing_unit_id="r1",
            target_unit_id="b1",
            fire_mode="reaction",
            reaction_trigger="entry",
        ),
    )

    assert result.ok
    assert result.missile_outcome is not None
    assert result.missile_outcome.fire_mode == "reaction"
    assert result.missile_outcome.reaction_trigger == "entry"
    assert [event.event_type for event in result.events] == [
        "missile_fired",
        "reaction_fire",
        "supply_changed",
        "reaction_window_spent",
    ]


def test_reaction_fire_rejects_spent_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reaction fire should fail when same window was already consumed."""

    spent_window = ReactionWindow(firing_unit_id="r1", target_unit_id="b1", reaction_trigger="entry")
    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        },
        active_side=Side.BLUE,
        spent_reaction_windows=(spent_window,),
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=8))

    result = resolve_missile(
        state,
        MissileAction(
            firing_unit_id="r1",
            target_unit_id="b1",
            fire_mode="reaction",
            reaction_trigger="entry",
        ),
    )

    assert not result.ok
    assert result.reason == "reaction_window_spent"


def test_fire_reload_sequence_updates_supply_and_events(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two fires and one reload should move supply normal->low->no->low."""

    state = _build_state(
        units={
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), missile_class_id="A"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0)),
        }
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=8))

    first_fire = resolve_missile(state, MissileAction(firing_unit_id="r1", target_unit_id="b1"))
    assert first_fire.ok
    assert first_fire.state.units["r1"].missile_supply == MissileSupply.LOW

    second_fire = resolve_missile(first_fire.state, MissileAction(firing_unit_id="r1", target_unit_id="b1"))
    assert second_fire.ok
    assert second_fire.state.units["r1"].missile_supply == MissileSupply.NO

    reload_state = second_fire.state.with_turn_phase(TurnPhase.ROUT_AND_RELOAD)
    reload = resolve_reload(reload_state, ReloadMissileAction(unit_id="r1"))
    assert reload.ok
    assert reload.state.units["r1"].missile_supply == MissileSupply.LOW
    assert [event.event_type for event in reload.events] == ["reload_attempt", "supply_changed"]
    assert reload.events[0].details["success"] is True


def test_reload_rejects_outside_reload_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reload should fail outside rout-and-reload phase."""

    state = _build_state(
        units={
            "r1": Unit(
                unit_id="r1",
                side=Side.RED,
                position=HexCoord(0, 0),
                missile_class_id="A",
                missile_supply=MissileSupply.LOW,
            )
        },
        turn_phase=TurnPhase.ORDERS,
    )
    monkeypatch.setattr(missile_rules, "load_table", lambda table_id: _missile_table(strength_at_range_one=8))

    result = resolve_reload(state, ReloadMissileAction(unit_id="r1"))

    assert not result.ok
    assert result.reason == "wrong_turn_phase"


def _build_state(
    units: dict[str, Unit],
    tiles: list[HexTile] | None = None,
    active_side: Side = Side.RED,
    turn_phase: TurnPhase = TurnPhase.ORDERS,
    open_reaction_windows: tuple[ReactionWindow, ...] = (),
    spent_reaction_windows: tuple[ReactionWindow, ...] = (),
) -> GameState:
    """Create a tiny deterministic battlefield for missile tests."""

    scenario_tiles = tiles or [
        HexTile(coord=HexCoord(0, 0)),
        HexTile(coord=HexCoord(1, 0)),
        HexTile(coord=HexCoord(2, 0)),
    ]
    scenario_map = build_irregular_map(tiles=scenario_tiles)
    return GameState.from_units(
        scenario_map=scenario_map,
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=active_side,
        units=units,
        turn_phase=turn_phase,
        open_reaction_windows=open_reaction_windows,
        spent_reaction_windows=spent_reaction_windows,
    )


def _missile_table(strength_at_range_one: int, strength_at_range_two: int | None = None) -> MissileTableModel:
    """Build minimal missile table fixture for resolver tests."""

    strength_by_range: dict[str, int] = {"1": strength_at_range_one}
    if strength_at_range_two is not None:
        strength_by_range["2"] = strength_at_range_two

    return MissileTableModel.model_validate(
        {
            "table_id": "missile_range_results",
            "version": "test",
            "missile_classes": [
                {
                    "missile_class_id": "A",
                    "name": "archer",
                    "strength_by_range": strength_by_range,
                }
            ],
            "dr_modifiers": [
                {"id": "target_woods", "drm": 2},
                {"id": "target_sk", "drm": -1},
                {"id": "firing_unit_depleted", "drm": 1},
            ],
        }
    )
