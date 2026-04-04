"""Game state models."""

from __future__ import annotations

from dataclasses import dataclass

from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import ScenarioMap
from legions_api.core.model.ruleset import RulesetDefinition
from legions_api.core.model.unit import Side, Unit


@dataclass(frozen=True, slots=True)
class GameState:
    """Minimal immutable state used by the movement engine."""

    scenario_map: ScenarioMap
    ruleset: RulesetDefinition
    active_side: Side
    units: dict[str, Unit]
    occupant_by_hex: dict[HexCoord, tuple[str, ...]]

    @classmethod
    def from_units(
        cls,
        scenario_map: ScenarioMap,
        ruleset: RulesetDefinition,
        active_side: Side,
        units: dict[str, Unit],
    ) -> GameState:
        """Create state and build occupancy index from units."""

        occupant_by_hex: dict[HexCoord, list[str]] = {}
        for unit_id, unit in units.items():
            if not scenario_map.contains(unit.position):
                raise ValueError(f"unit {unit_id} starts outside passable map")
            occupants = occupant_by_hex.setdefault(unit.position, [])
            occupants.append(unit_id)

        frozen_occupants = {
            coord: tuple(unit_ids)
            for coord, unit_ids in occupant_by_hex.items()
        }

        return cls(
            scenario_map=scenario_map,
            ruleset=ruleset,
            active_side=active_side,
            units=units,
            occupant_by_hex=frozen_occupants,
        )

    def unit_at(self, coord: HexCoord) -> Unit | None:
        """Return unit occupying coordinate, if any."""

        unit_ids = self.occupant_by_hex.get(coord)
        if not unit_ids:
            return None

        return self.units[unit_ids[0]]

    def units_at(self, coord: HexCoord) -> tuple[Unit, ...]:
        """Return all units occupying coordinate, preserving insertion order."""

        unit_ids = self.occupant_by_hex.get(coord, ())
        return tuple(self.units[unit_id] for unit_id in unit_ids)

    def with_units(self, units: dict[str, Unit]) -> GameState:
        """Return a copy with replaced units dictionary."""

        return GameState.from_units(
            scenario_map=self.scenario_map,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=units,
        )

    def with_active_side(self, active_side: Side) -> GameState:
        """Return a copy with updated active side."""

        return GameState(
            scenario_map=self.scenario_map,
            ruleset=self.ruleset,
            active_side=active_side,
            units=self.units,
            occupant_by_hex=self.occupant_by_hex,
        )
