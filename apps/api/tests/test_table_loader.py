"""Tests for rules table loading and validation."""

from __future__ import annotations

import pytest

from legions_api.core.model.map import TerrainType
from legions_api.core.model.ruleset import RulesetMode
from legions_api.core.tables import loader as table_loader
from legions_api.core.tables.loader import TableId, load_ruleset, load_supported_tables, load_table
from legions_api.core.tables.models import MissileTableModel, MovementCostsTableModel


@pytest.mark.parametrize("table_id", [
    "movement_costs",
    "stacking_voluntary",
    "stacking_mandatory",
    "missile_range_results",
    "shock_superiority",
    "clash_columns",
    "shock_crt",
    "rally_table",
    "leader_casualty_table",
])
def test_known_table_templates_load_and_validate(table_id: TableId) -> None:
    """Known table templates should be parseable with typed models."""

    load_table.cache_clear()
    table = load_table(table_id)
    assert table.table_id == table_id


def test_load_table_raises_for_missing_table_file() -> None:
    """Loading unknown table id should fail at runtime."""

    load_table.cache_clear()
    with pytest.raises(FileNotFoundError):
        load_table("unknown_table")  # type: ignore[arg-type]  # runtime-guard test


def test_load_supported_tables_returns_all_known_ids() -> None:
    """Bulk loader should return every currently supported table."""

    load_table.cache_clear()
    tables = load_supported_tables()
    assert set(tables) == {
        "movement_costs",
        "stacking_voluntary",
        "stacking_mandatory",
        "missile_range_results",
        "shock_superiority",
        "clash_columns",
        "shock_crt",
        "rally_table",
        "leader_casualty_table",
    }


def test_ruleset_uses_table_driven_movement_profile_lookup() -> None:
    """Rulesets should resolve terrain costs through configured movement profiles."""

    load_table.cache_clear()
    load_ruleset.cache_clear()

    original = load_ruleset(RulesetMode.ORIGINAL)
    simple = load_ruleset(RulesetMode.SIMPLE)

    assert original.default_movement_profile_id == "original_standard"
    assert simple.default_movement_profile_id == "simple_standard"
    assert original.movement_cost_for_terrain(TerrainType.ROUGH) == 2
    assert simple.movement_cost_for_terrain(TerrainType.ROUGH) == 1


def test_load_ruleset_fails_when_movement_profile_misses_terrain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ruleset loading should fail fast when movement profile is incomplete."""

    incomplete_table = MovementCostsTableModel.model_validate(
        {
            "table_id": "movement_costs",
            "version": "test",
            "terrain_types": ["clear", "rough", "woods", "road", "water"],
            "unit_profiles": [
                {
                    "unit_profile_id": "original_standard",
                    "aliases": [],
                    "base_ma": 4,
                    "extended_ma": None,
                    "terrain_costs": {
                        "clear": {"mp": 1, "cohesion_hits": 0},
                        "rough": {"mp": 2, "cohesion_hits": 0},
                        "woods": {"mp": 2, "cohesion_hits": 0},
                        "road": {"mp": 1, "cohesion_hits": 0}
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

    load_ruleset.cache_clear()
    monkeypatch.setattr(table_loader, "load_table", lambda table_id: incomplete_table)

    with pytest.raises(ValueError, match="misses terrain costs"):
        load_ruleset(RulesetMode.ORIGINAL)


def test_load_ruleset_fails_for_unknown_profile_terrain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ruleset loading should reject movement profiles with unknown terrain ids."""

    invalid_terrain_table = MovementCostsTableModel.model_validate(
        {
            "table_id": "movement_costs",
            "version": "test",
            "terrain_types": ["clear", "rough", "woods", "road", "water", "lava"],
            "unit_profiles": [
                {
                    "unit_profile_id": "original_standard",
                    "aliases": [],
                    "base_ma": 4,
                    "extended_ma": None,
                    "terrain_costs": {
                        "clear": {"mp": 1, "cohesion_hits": 0},
                        "rough": {"mp": 2, "cohesion_hits": 0},
                        "woods": {"mp": 2, "cohesion_hits": 0},
                        "road": {"mp": 1, "cohesion_hits": 0},
                        "water": {"mp": 99, "cohesion_hits": None},
                        "lava": {"mp": 9, "cohesion_hits": 3}
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

    load_ruleset.cache_clear()
    monkeypatch.setattr(table_loader, "load_table", lambda table_id: invalid_terrain_table)

    with pytest.raises(ValueError, match="unknown terrain"):
        load_ruleset(RulesetMode.ORIGINAL)


def test_validate_stacking_pair_matrix_rejects_duplicates() -> None:
    """Stacking matrix validator should reject duplicate category pairs."""

    with pytest.raises(ValueError, match="duplicate category rows"):
        table_loader._validate_stacking_pair_matrix(
            table_id="stacking_voluntary",
            keys=[("basic", "basic"), ("basic", "basic")],
        )


def test_validate_stacking_pair_matrix_rejects_missing_pairs() -> None:
    """Stacking matrix validator should reject incomplete moving/stationary matrix."""

    with pytest.raises(ValueError, match="misses category pairs"):
        table_loader._validate_stacking_pair_matrix(
            table_id="stacking_voluntary",
            keys=[("basic", "basic"), ("basic", "scout"), ("scout", "basic")],
        )


def test_missile_table_validator_rejects_duplicate_class_ids() -> None:
    """Missile table validation should fail when class ids are duplicated."""

    table = MissileTableModel.model_validate(
        {
            "table_id": "missile_range_results",
            "version": "test",
            "missile_classes": [
                {"missile_class_id": "A", "name": "archer", "strength_by_range": {"1": 7}},
                {"missile_class_id": "A", "name": "archer2", "strength_by_range": {"1": 6}},
            ],
            "dr_modifiers": [{"id": "target_woods", "drm": 2}],
        }
    )

    with pytest.raises(ValueError, match="duplicate missile class ids"):
        table_loader._validate_missile_table(table)


def test_missile_table_validator_rejects_duplicate_modifier_ids() -> None:
    """Missile table validation should fail when DR modifier ids are duplicated."""

    table = MissileTableModel.model_validate(
        {
            "table_id": "missile_range_results",
            "version": "test",
            "missile_classes": [
                {"missile_class_id": "A", "name": "archer", "strength_by_range": {"1": 7}}
            ],
            "dr_modifiers": [
                {"id": "target_woods", "drm": 2},
                {"id": "target_woods", "drm": 1},
            ],
        }
    )

    with pytest.raises(ValueError, match="duplicate DR modifier ids"):
        table_loader._validate_missile_table(table)


def test_missile_class_model_rejects_non_contiguous_ranges() -> None:
    """Missile class ranges should be contiguous from 1 to max range."""

    with pytest.raises(ValueError, match="must define contiguous ranges"):
        MissileTableModel.model_validate(
            {
                "table_id": "missile_range_results",
                "version": "test",
                "missile_classes": [
                    {
                        "missile_class_id": "A",
                        "name": "archer",
                        "strength_by_range": {"1": 7, "3": 5},
                    }
                ],
                "dr_modifiers": [{"id": "target_woods", "drm": 2}],
            }
        )


def test_missile_class_model_rejects_non_numeric_ranges() -> None:
    """Missile class ranges should be numeric range bands."""

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
                "dr_modifiers": [{"id": "target_woods", "drm": 2}],
            }
        )
