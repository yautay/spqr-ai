"""Tests for rules table loading and validation."""

from __future__ import annotations

import pytest

from legions_api.core.tables.loader import TableId, load_supported_tables, load_table


@pytest.mark.parametrize("table_id", [
    "movement_costs",
    "stacking_voluntary",
    "stacking_mandatory",
    "missile_range_results",
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
        "rally_table",
        "leader_casualty_table",
    }
