"""Game state models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from legions_api.core.model.hex import HexCoord
from legions_api.core.model.map import ScenarioMap
from legions_api.core.model.ruleset import RulesetDefinition
from legions_api.core.model.unit import Side, Unit

ReactionTrigger = Literal["entry", "retire", "return"]


class TurnPhase(StrEnum):
    """Minimal turn phase marker used by action validation."""

    ORDERS = "orders"
    ROUT_AND_RELOAD = "rout_and_reload"


@dataclass(frozen=True, slots=True)
class ReactionWindow:
    """One reaction fire eligibility window opened by movement."""

    firing_unit_id: str
    target_unit_id: str
    reaction_trigger: ReactionTrigger


@dataclass(frozen=True, slots=True)
class GameState:
    """Minimal immutable state used by the movement engine."""

    scenario_map: ScenarioMap
    ruleset: RulesetDefinition
    active_side: Side
    units: dict[str, Unit]
    occupant_by_hex: dict[HexCoord, tuple[str, ...]]
    rng_seed: int
    rng_counter: int
    turn_phase: TurnPhase
    open_reaction_windows: tuple[ReactionWindow, ...]
    spent_reaction_windows: tuple[ReactionWindow, ...]

    @classmethod
    def from_units(
        cls,
        scenario_map: ScenarioMap,
        ruleset: RulesetDefinition,
        active_side: Side,
        units: dict[str, Unit],
        rng_seed: int = 1,
        rng_counter: int = 0,
        turn_phase: TurnPhase = TurnPhase.ORDERS,
        open_reaction_windows: tuple[ReactionWindow, ...] = (),
        spent_reaction_windows: tuple[ReactionWindow, ...] = (),
    ) -> GameState:
        """Create state and build occupancy index from units."""

        occupant_by_hex: dict[HexCoord, list[str]] = {}
        for unit_id, unit in units.items():
            if not scenario_map.contains(unit.position):
                raise ValueError(f"unit {unit_id} starts outside passable map")
            occupants = occupant_by_hex.setdefault(unit.position, [])
            occupants.append(unit_id)

        frozen_occupants = {coord: tuple(unit_ids) for coord, unit_ids in occupant_by_hex.items()}

        return cls(
            scenario_map=scenario_map,
            ruleset=ruleset,
            active_side=active_side,
            units=units,
            occupant_by_hex=frozen_occupants,
            rng_seed=rng_seed,
            rng_counter=rng_counter,
            turn_phase=turn_phase,
            open_reaction_windows=open_reaction_windows,
            spent_reaction_windows=spent_reaction_windows,
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
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_phase=self.turn_phase,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_active_side(self, active_side: Side) -> GameState:
        """Return a copy with updated active side."""

        return GameState(
            scenario_map=self.scenario_map,
            ruleset=self.ruleset,
            active_side=active_side,
            units=self.units,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_phase=self.turn_phase,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_rng_counter(self, rng_counter: int) -> GameState:
        """Return copy with updated RNG counter."""

        return GameState(
            scenario_map=self.scenario_map,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=rng_counter,
            turn_phase=self.turn_phase,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_turn_phase(self, turn_phase: TurnPhase) -> GameState:
        """Return copy with updated turn phase."""

        return GameState(
            scenario_map=self.scenario_map,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_phase=turn_phase,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_reaction_windows(
        self,
        open_reaction_windows: tuple[ReactionWindow, ...],
        spent_reaction_windows: tuple[ReactionWindow, ...] = (),
    ) -> GameState:
        """Return copy with replaced reaction window state."""

        return GameState(
            scenario_map=self.scenario_map,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_phase=self.turn_phase,
            open_reaction_windows=open_reaction_windows,
            spent_reaction_windows=spent_reaction_windows,
        )

    def is_reaction_window_open(self, firing_unit_id: str, target_unit_id: str, reaction_trigger: ReactionTrigger) -> bool:
        """Return whether specific reaction window is currently open."""

        candidate = ReactionWindow(
            firing_unit_id=firing_unit_id,
            target_unit_id=target_unit_id,
            reaction_trigger=reaction_trigger,
        )
        return candidate in self.open_reaction_windows

    def is_reaction_window_spent(self, firing_unit_id: str, target_unit_id: str, reaction_trigger: ReactionTrigger) -> bool:
        """Return whether specific reaction window was already consumed."""

        candidate = ReactionWindow(
            firing_unit_id=firing_unit_id,
            target_unit_id=target_unit_id,
            reaction_trigger=reaction_trigger,
        )
        return candidate in self.spent_reaction_windows

    def mark_reaction_window_spent(
        self,
        firing_unit_id: str,
        target_unit_id: str,
        reaction_trigger: ReactionTrigger,
    ) -> GameState:
        """Move one window from open to spent list if currently open."""

        candidate = ReactionWindow(
            firing_unit_id=firing_unit_id,
            target_unit_id=target_unit_id,
            reaction_trigger=reaction_trigger,
        )
        if candidate not in self.open_reaction_windows:
            return self

        next_open_windows = tuple(window for window in self.open_reaction_windows if window != candidate)
        next_spent_windows = self.spent_reaction_windows
        if candidate not in next_spent_windows:
            next_spent_windows = (*next_spent_windows, candidate)

        return GameState(
            scenario_map=self.scenario_map,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_phase=self.turn_phase,
            open_reaction_windows=next_open_windows,
            spent_reaction_windows=next_spent_windows,
        )
