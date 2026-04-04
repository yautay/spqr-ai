"""Tests for runtime table adapter helpers."""

from __future__ import annotations

import pytest

from legions_api.core.model.map import TerrainType
from legions_api.core.tables.adapters import mandatory_stacking_lookup, missile_class_lookup, movement_costs_by_profile, voluntary_stacking_lookup
from legions_api.core.tables.models import MissileTableModel, MovementCostsTableModel, StackingMandatoryTableModel, StackingVoluntaryTableModel


def test_movement_costs_by_profile_raises_for_unknown_terrain() -> None:
    """Movement adapter should fail when profile uses unsupported terrain id."""

    table = MovementCostsTableModel.model_validate(
        {
            "table_id": "movement_costs",
            "version": "test",
            "terrain_types": ["clear", "lava"],
            "unit_profiles": [
                {
                    "unit_profile_id": "p1",
                    "aliases": [],
                    "base_ma": 4,
                    "extended_ma": None,
                    "terrain_costs": {
                        "clear": {"mp": 1, "cohesion_hits": 0},
                        "lava": {"mp": 9, "cohesion_hits": 2}
                    },
                    "elevation": {
                        "up_one": {"mp": 1, "cohesion_hits": 0},
                        "up_two_or_more": {"mp": 2, "cohesion_hits": 1}
                    },
                    "facing_change": {
                        "mp_per_vertex": 1,
                        "cohesion_hits_per_vertex_in_rough": 0
                    }
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="unknown terrain"):
        movement_costs_by_profile(table)


def test_movement_costs_by_profile_returns_enum_keyed_costs() -> None:
    """Movement adapter should return TerrainType-keyed profile lookup."""

    table = MovementCostsTableModel.model_validate(
        {
            "table_id": "movement_costs",
            "version": "test",
            "terrain_types": ["clear", "rough"],
            "unit_profiles": [
                {
                    "unit_profile_id": "p1",
                    "aliases": [],
                    "base_ma": 4,
                    "extended_ma": None,
                    "terrain_costs": {
                        "clear": {"mp": 1, "cohesion_hits": 0},
                        "rough": {"mp": 2, "cohesion_hits": 1}
                    },
                    "elevation": {
                        "up_one": {"mp": 1, "cohesion_hits": 0},
                        "up_two_or_more": {"mp": 2, "cohesion_hits": 1}
                    },
                    "facing_change": {
                        "mp_per_vertex": 1,
                        "cohesion_hits_per_vertex_in_rough": 0
                    }
                }
            ]
        }
    )

    result = movement_costs_by_profile(table)

    assert result["p1"][TerrainType.CLEAR] == 1
    assert result["p1"][TerrainType.ROUGH] == 2


def test_voluntary_stacking_lookup_rejects_duplicate_keys() -> None:
    """Voluntary lookup should fail on duplicate category pair rows."""

    table = StackingVoluntaryTableModel.model_validate(
        {
            "table_id": "stacking_voluntary",
            "version": "test",
            "rows": [
                {
                    "moving_category": "basic",
                    "stationary_category": "basic",
                    "may_move_through": False,
                    "may_stop_in_hex": False,
                    "moving_unit_cohesion_hits": None,
                    "stationary_unit_cohesion_hits": None,
                    "tq_check_drm": None
                },
                {
                    "moving_category": "basic",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": False,
                    "moving_unit_cohesion_hits": 1,
                    "stationary_unit_cohesion_hits": 1,
                    "tq_check_drm": -1
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="duplicate voluntary stacking row"):
        voluntary_stacking_lookup(table)


def test_mandatory_stacking_lookup_maps_tq_fields() -> None:
    """Mandatory lookup should carry TQ-check metadata into runtime outcome."""

    table = StackingMandatoryTableModel.model_validate(
        {
            "table_id": "stacking_mandatory",
            "version": "test",
            "rows": [
                {
                    "moving_category": "routing_basic",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": False,
                    "moving_unit_cohesion_hits": 1,
                    "stationary_unit_cohesion_hits": 2,
                    "stationary_unit_tq_check": {
                        "required": True,
                        "formula": "tq-2"
                    }
                }
            ]
        }
    )

    lookup = mandatory_stacking_lookup(table)
    outcome = lookup[("routing_basic", "basic")]

    assert outcome.may_move_through
    assert not outcome.may_stop_in_hex
    assert outcome.stationary_unit_tq_check_required
    assert outcome.stationary_unit_tq_check_formula == "tq-2"
    assert outcome.tq_check_drm is None


def test_missile_class_lookup_builds_numeric_range_lookup() -> None:
    """Missile adapter should normalize range bands to int keys."""

    table = MissileTableModel.model_validate(
        {
            "table_id": "missile_range_results",
            "version": "test",
            "missile_classes": [
                {
                    "missile_class_id": "A",
                    "name": "archer",
                    "strength_by_range": {"1": 7, "2": 5, "3": None},
                }
            ],
            "dr_modifiers": [],
        }
    )

    lookup = missile_class_lookup(table)

    assert lookup["A"].strengths_by_range[1] == 7
    assert lookup["A"].strengths_by_range[2] == 5
    assert 3 not in lookup["A"].strengths_by_range


def test_missile_class_lookup_rejects_non_numeric_range_band() -> None:
    """Missile adapter should fail fast for invalid range keys."""

    table = MissileTableModel.model_validate(
        {
            "table_id": "missile_range_results",
            "version": "test",
            "missile_classes": [
                {
                    "missile_class_id": "A",
                    "name": "archer",
                    "strength_by_range": {"adjacent": 7},
                }
            ],
            "dr_modifiers": [],
        }
    )

    with pytest.raises(ValueError, match="non-numeric range band"):
        missile_class_lookup(table)
