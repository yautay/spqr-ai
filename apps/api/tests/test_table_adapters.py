"""Tests for runtime table adapter helpers."""

from __future__ import annotations

import pytest

from legions_api.core.model.map import TerrainType
from legions_api.core.tables.adapters import (
    clash_column_lookup,
    mandatory_stacking_lookup,
    missile_class_lookup,
    missile_drm_lookup,
    movement_costs_by_profile,
    pursuit_option_lookup,
    shock_column_adjustment_lookup,
    shock_crt_lookup,
    shock_superiority_lookup,
    unit_type_traits_lookup,
    voluntary_stacking_lookup,
)
from legions_api.core.tables.models import (
    ClashColumnsTableModel,
    MissileTableModel,
    MovementCostsTableModel,
    PursuitOptionTableModel,
    ShockCRTTableModel,
    ShockSuperiorityTableModel,
    StackingMandatoryTableModel,
    StackingVoluntaryTableModel,
    UnitTypeTraitsTableModel,
)


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
                    "terrain_costs": {"clear": {"mp": 1, "cohesion_hits": 0}, "lava": {"mp": 9, "cohesion_hits": 2}},
                    "elevation": {"up_one": {"mp": 1, "cohesion_hits": 0}, "up_two_or_more": {"mp": 2, "cohesion_hits": 1}},
                    "facing_change": {"mp_per_vertex": 1, "cohesion_hits_per_vertex_in_rough": 0},
                }
            ],
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
                    "terrain_costs": {"clear": {"mp": 1, "cohesion_hits": 0}, "rough": {"mp": 2, "cohesion_hits": 1}},
                    "elevation": {"up_one": {"mp": 1, "cohesion_hits": 0}, "up_two_or_more": {"mp": 2, "cohesion_hits": 1}},
                    "facing_change": {"mp_per_vertex": 1, "cohesion_hits_per_vertex_in_rough": 0},
                }
            ],
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
                    "tq_check_drm": None,
                },
                {
                    "moving_category": "basic",
                    "stationary_category": "basic",
                    "may_move_through": True,
                    "may_stop_in_hex": False,
                    "moving_unit_cohesion_hits": 1,
                    "stationary_unit_cohesion_hits": 1,
                    "tq_check_drm": -1,
                },
            ],
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
                    "stationary_unit_tq_check": {"required": True, "formula": "tq-2"},
                }
            ],
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
                    "strength_by_range": {"1": 7, "2": 5},
                }
            ],
            "dr_modifiers": [],
        }
    )

    lookup = missile_class_lookup(table)

    assert lookup["A"].strengths_by_range[1] == 7
    assert lookup["A"].strengths_by_range[2] == 5


def test_missile_class_lookup_rejects_non_numeric_range_band() -> None:
    """Missile adapter should fail fast for invalid range keys."""

    with pytest.raises(ValueError, match="non-numeric range band"):
        MissileTableModel.model_validate(
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


def test_missile_drm_lookup_returns_modifier_values() -> None:
    """Missile DRM adapter should expose id-keyed integer modifier values."""

    table = MissileTableModel.model_validate(
        {
            "table_id": "missile_range_results",
            "version": "test",
            "missile_classes": [
                {
                    "missile_class_id": "A",
                    "name": "archer",
                    "strength_by_range": {"1": 7},
                }
            ],
            "dr_modifiers": [
                {"id": "target_woods", "drm": 2},
                {"id": "target_sk", "drm": -1},
            ],
        }
    )

    lookup = missile_drm_lookup(table)

    assert lookup["target_woods"].drm == 2
    assert lookup["target_sk"].drm == -1


def test_shock_superiority_lookup_maps_outcomes_to_shifts() -> None:
    """Shock superiority adapter should normalize attacker/defender outcomes to shifts."""

    table = ShockSuperiorityTableModel.model_validate(
        {
            "table_id": "shock_superiority",
            "version": "test",
            "attacker_types": ["HI"],
            "defender_types": ["HC", "SK"],
            "matrix": [
                {
                    "attacker_type": "HI",
                    "results": {
                        "HC": "defender",
                        "SK": "attacker",
                    },
                }
            ],
        }
    )

    lookup = shock_superiority_lookup(table)

    assert lookup[("HI", "HC")] == -1
    assert lookup[("HI", "SK")] == 1


def test_clash_column_lookup_uses_attacker_defender_angle_key() -> None:
    """Clash adapter should return base column by matchup and angle."""

    table = ClashColumnsTableModel.model_validate(
        {
            "table_id": "clash_columns",
            "version": "test",
            "angles": ["front", "flank", "rear"],
            "entries": [
                {
                    "attacker_type": "HI",
                    "defender_type": "HI",
                    "angle": "front",
                    "base_column": 5,
                }
            ],
        }
    )

    lookup = clash_column_lookup(table)

    assert lookup[("HI", "HI", "front")] == 5


def test_shock_crt_lookup_parses_int_keyed_cells() -> None:
    """Shock CRT adapter should normalize string keys to integer lookup keys."""

    table = ShockCRTTableModel.model_validate(
        {
            "table_id": "shock_crt",
            "version": "test",
            "columns": ["1"],
            "rows": ["1"],
            "cells": {"1": {"1": {"attacker_hits": 1, "defender_hits": 2}}},
            "column_adjustments": [],
        }
    )

    lookup = shock_crt_lookup(table)

    assert lookup[(1, 1)].attacker_hits == 1
    assert lookup[(1, 1)].defender_hits == 2


def test_shock_column_adjustment_lookup_converts_direction_to_shift() -> None:
    """Shock adjustment adapter should convert left/right metadata to signed shifts."""

    table = ShockCRTTableModel.model_validate(
        {
            "table_id": "shock_crt",
            "version": "test",
            "columns": ["1"],
            "rows": ["1"],
            "cells": {"1": {"1": {"attacker_hits": 0, "defender_hits": 0}}},
            "column_adjustments": [
                {"id": "charge", "direction": "right", "value": 1},
                {"id": "rough", "direction": "left", "value": 2},
            ],
        }
    )

    lookup = shock_column_adjustment_lookup(table)

    assert lookup["charge"].shift == 1
    assert lookup["rough"].shift == -2


def test_pursuit_option_lookup_builds_rating_and_modifier_maps() -> None:
    """Pursuit option adapter should map ratings and DR modifiers."""

    table = PursuitOptionTableModel.model_validate(
        {
            "table_id": "pursuit_option",
            "version": "test",
            "ratings": {"LC": 5, "HC": 7},
            "dr_modifiers": [
                {"id": "numidian_lc", "drm": -1},
                {"id": "attacker_in_enemy_zoc", "drm": 1},
            ],
        }
    )

    lookup = pursuit_option_lookup(table)

    assert lookup.ratings["LC"] == 5
    assert lookup.dr_modifiers["numidian_lc"] == -1


def test_unit_type_traits_lookup_rejects_duplicate_unit_types() -> None:
    """Unit traits adapter should reject duplicated unit type rows."""

    table = UnitTypeTraitsTableModel.model_validate(
        {
            "table_id": "unit_type_traits",
            "version": "test",
            "unit_types": [
                {"unit_type": "HI", "traits": {"is_cavalry": False}},
                {"unit_type": "HI", "traits": {"is_cavalry": True}},
            ],
        }
    )

    with pytest.raises(ValueError, match="duplicate unit_type traits row"):
        unit_type_traits_lookup(table)
