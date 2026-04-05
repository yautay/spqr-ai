"""Shock combat rule tests."""

from __future__ import annotations

import pytest

from legions_api.core.actions import ShockAction
from legions_api.core.model.game_state import GameState, TurnPhase
from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import HexTile, build_irregular_map
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.model.scenario import ScenarioDefinition
from legions_api.core.model.unit import Side, Unit
from legions_api.core.rules import shock as shock_rules
from legions_api.core.rules.shock import resolve_shock
from legions_api.core.tables.loader import load_ruleset
from legions_api.core.tables.models import ClashColumnsTableModel, ShockCRTTableModel, ShockSuperiorityTableModel


def test_shock_rejects_non_adjacent_targets() -> None:
    """Shock attack should fail when units are not adjacent."""

    state = _build_state(
        {
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0)),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(2, 0)),
        }
    )

    result = resolve_shock(state, ShockAction(attacker_unit_id="r1", defender_unit_id="b1"))

    assert not result.ok
    assert result.reason == "shock_not_adjacent"


def test_shock_applies_crt_hits_and_advances_rng(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shock resolver should apply CRT hits to both units and advance RNG."""

    state = _build_state(
        {
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), shock_type="HI", tq=10),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), shock_type="HI", tq=10),
        }
    )
    _patch_shock_tables(monkeypatch)

    result = resolve_shock(state, ShockAction(attacker_unit_id="r1", defender_unit_id="b1"))

    assert result.ok
    assert result.shock_outcome is not None
    assert result.shock_outcome.base_column == 5
    assert result.shock_outcome.final_column == 5
    assert result.shock_outcome.roll == 6
    assert result.shock_outcome.attacker_hits == 1
    assert result.shock_outcome.defender_hits == 1
    assert result.state.units["r1"].cohesion_hits == 1
    assert result.state.units["b1"].cohesion_hits == 1
    assert result.state.rng_counter == 3
    assert result.events[0].event_type == "shock_designated"
    assert result.events[1].event_type == "shock_resolved"
    assert any(event.event_type == "morale_resolved" for event in result.events)


def test_shock_applies_superiority_and_explicit_modifier_shifts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Superiority and explicit modifiers should move column and raise defender hits."""

    state = _build_state(
        {
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), shock_type="HC", tq=10),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), shock_type="HI", tq=10),
        }
    )
    _patch_shock_tables(monkeypatch)

    result = resolve_shock(
        state,
        ShockAction(
            attacker_unit_id="r1",
            defender_unit_id="b1",
            modifier_ids=("attacker_charging",),
        ),
    )

    assert result.ok
    assert result.shock_outcome is not None
    assert result.shock_outcome.base_column == 6
    assert result.shock_outcome.total_shift == 2
    assert result.shock_outcome.final_column == 8
    assert [entry.id for entry in result.shock_outcome.modifier_breakdown] == ["superiority_attacker", "attacker_charging"]
    assert result.state.units["b1"].cohesion_hits == 4


def test_shock_rejects_unknown_modifier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shock resolver should fail for modifier ids absent from CRT metadata."""

    state = _build_state(
        {
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), shock_type="HI"),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), shock_type="HI"),
        }
    )
    _patch_shock_tables(monkeypatch)

    result = resolve_shock(
        state,
        ShockAction(attacker_unit_id="r1", defender_unit_id="b1", modifier_ids=("unknown",)),
    )

    assert not result.ok
    assert result.reason == "unknown_shock_modifier"


def test_shock_failed_morale_routes_and_retreated_unit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed morale should mark unit routed and force one-hex retreat."""

    state = _build_state(
        {
            "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), shock_type="HC", tq=10),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), shock_type="HI", tq=3),
        }
    )
    _patch_shock_tables(monkeypatch)

    result = resolve_shock(state, ShockAction(attacker_unit_id="r1", defender_unit_id="b1"))

    assert result.ok
    assert result.state.units["b1"].is_routed
    assert result.state.units["b1"].position == HexCoord(2, 0)
    defender_morale = {entry.unit_id: entry for entry in result.morale_outcomes}["b1"]
    assert defender_morale.became_routed
    assert defender_morale.retreated
    assert not defender_morale.eliminated


def test_shock_cavalry_pursuit_moves_into_vacated_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pursuit-capable attacker should move into defender origin after rout retreat."""

    state = _build_state(
        {
            "r1": Unit(
                unit_id="r1",
                side=Side.RED,
                position=HexCoord(0, 0),
                shock_type="HC",
                tq=10,
                pursuit_capable=True,
            ),
            "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), shock_type="HI", tq=3),
        }
    )
    _patch_shock_tables(monkeypatch)

    result = resolve_shock(state, ShockAction(attacker_unit_id="r1", defender_unit_id="b1"))

    assert result.ok
    assert result.pursuit_outcome is not None
    assert result.pursuit_outcome.unit_id == "r1"
    assert result.pursuit_outcome.destination == HexCoord(1, 0)
    assert result.state.units["r1"].position == HexCoord(1, 0)


def test_shock_eliminates_routed_unit_when_retreat_hex_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed morale should eliminate routed unit when retreat hex is off-map or blocked."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
        ]
    )
    units = {
        "r1": Unit(unit_id="r1", side=Side.RED, position=HexCoord(0, 0), shock_type="HC", tq=10),
        "b1": Unit(unit_id="b1", side=Side.BLUE, position=HexCoord(1, 0), shock_type="HI", tq=3),
    }
    state = GameState.from_units(
        scenario_map=scenario_map,
        scenario=ScenarioDefinition(),
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
        turn_phase=TurnPhase.SHOCK,
    )
    _patch_shock_tables(monkeypatch)

    result = resolve_shock(state, ShockAction(attacker_unit_id="r1", defender_unit_id="b1"))

    assert result.ok
    assert "b1" not in result.state.units
    defender_morale = {entry.unit_id: entry for entry in result.morale_outcomes}["b1"]
    assert defender_morale.eliminated


def _patch_shock_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch loader in shock module with deterministic table fixtures."""

    tables = {
        "shock_superiority": ShockSuperiorityTableModel.model_validate(
            {
                "table_id": "shock_superiority",
                "version": "test",
                "attacker_types": ["HI", "HC"],
                "defender_types": ["HI", "HC"],
                "matrix": [
                    {"attacker_type": "HI", "results": {"HI": "none", "HC": "defender"}},
                    {"attacker_type": "HC", "results": {"HI": "attacker", "HC": "none"}},
                ],
            }
        ),
        "clash_columns": ClashColumnsTableModel.model_validate(
            {
                "table_id": "clash_columns",
                "version": "test",
                "angles": ["front", "flank", "rear"],
                "entries": [
                    {"attacker_type": "HI", "defender_type": "HI", "angle": "front", "base_column": 5},
                    {"attacker_type": "HC", "defender_type": "HI", "angle": "front", "base_column": 6},
                ],
            }
        ),
        "shock_crt": ShockCRTTableModel.model_validate(
            {
                "table_id": "shock_crt",
                "version": "test",
                "columns": ["5", "6", "7", "8"],
                "rows": ["1", "6"],
                "cells": {
                    "5": {
                        "1": {"attacker_hits": 0, "defender_hits": 1},
                        "6": {"attacker_hits": 1, "defender_hits": 1},
                    },
                    "6": {
                        "1": {"attacker_hits": 0, "defender_hits": 2},
                        "6": {"attacker_hits": 1, "defender_hits": 2},
                    },
                    "7": {
                        "1": {"attacker_hits": 1, "defender_hits": 2},
                        "6": {"attacker_hits": 1, "defender_hits": 3},
                    },
                    "8": {
                        "1": {"attacker_hits": 1, "defender_hits": 3},
                        "6": {"attacker_hits": 1, "defender_hits": 4},
                    },
                },
                "column_adjustments": [
                    {"id": "superiority_attacker", "direction": "right", "value": 1},
                    {"id": "superiority_defender", "direction": "left", "value": 1},
                    {"id": "attacker_charging", "direction": "right", "value": 1},
                ],
            }
        ),
    }
    monkeypatch.setattr(shock_rules, "load_table", lambda table_id: tables[table_id])


def _build_state(units: dict[str, Unit]) -> GameState:
    """Create a tiny deterministic battlefield for shock tests."""

    scenario_map = build_irregular_map(
        tiles=[
            HexTile(coord=HexCoord(0, 0)),
            HexTile(coord=HexCoord(1, 0)),
            HexTile(coord=HexCoord(2, 0)),
        ]
    )
    return GameState.from_units(
        scenario_map=scenario_map,
        scenario=ScenarioDefinition(),
        ruleset=load_ruleset(RulesetMode.ORIGINAL),
        active_side=Side.RED,
        units=units,
        turn_phase=TurnPhase.SHOCK,
    )
