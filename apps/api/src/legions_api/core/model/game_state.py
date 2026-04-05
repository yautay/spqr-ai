"""Game state models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from legions_api.core.model.hex import HexCoord
from legions_api.core.model.leader import Leader, LeaderStatus
from legions_api.core.model.map import ScenarioMap
from legions_api.core.model.ruleset import RulesetDefinition
from legions_api.core.model.scenario import ScenarioDefinition
from legions_api.core.model.unit import Side, Unit

ReactionTrigger = Literal["entry", "retire", "return"]


class TurnPhase(StrEnum):
    """Runtime phase marker used by action validation and turn flow."""

    ORDERS = "orders"
    SHOCK = "shock"
    ROUT_AND_RELOAD = "rout_and_reload"
    WITHDRAWAL = "withdrawal"


@dataclass(frozen=True, slots=True)
class ReactionWindow:
    """One reaction fire eligibility window opened by movement."""

    firing_unit_id: str
    target_unit_id: str
    reaction_trigger: ReactionTrigger


@dataclass(frozen=True, slots=True)
class ActivationState:
    """Current leader-driven activation context."""

    leader_id: str | None = None
    orders_remaining: int = 0
    line_commands_remaining: int = 0
    moved_unit_ids: tuple[str, ...] = ()
    fired_unit_ids: tuple[str, ...] = ()
    shocked_unit_ids: tuple[str, ...] = ()
    activated_leader_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GameState:
    """Immutable runtime state for tactical rules execution."""

    scenario_map: ScenarioMap
    scenario: ScenarioDefinition
    ruleset: RulesetDefinition
    active_side: Side
    units: dict[str, Unit]
    leaders: dict[str, Leader]
    occupant_by_hex: dict[HexCoord, tuple[str, ...]]
    rng_seed: int
    rng_counter: int
    turn_number: int
    turn_phase: TurnPhase
    activation: ActivationState
    open_reaction_windows: tuple[ReactionWindow, ...]
    spent_reaction_windows: tuple[ReactionWindow, ...]

    @classmethod
    def from_units(
        cls,
        scenario_map: ScenarioMap,
        scenario: ScenarioDefinition,
        ruleset: RulesetDefinition,
        active_side: Side,
        units: dict[str, Unit],
        leaders: dict[str, Leader] | None = None,
        rng_seed: int = 1,
        rng_counter: int = 0,
        turn_number: int = 1,
        turn_phase: TurnPhase = TurnPhase.ORDERS,
        activation: ActivationState | None = None,
        open_reaction_windows: tuple[ReactionWindow, ...] = (),
        spent_reaction_windows: tuple[ReactionWindow, ...] = (),
    ) -> GameState:
        """Create state and build occupancy index from units."""

        leader_lookup = _normalize_leaders(active_side=active_side, units=units, leaders=leaders)
        occupant_by_hex: dict[HexCoord, list[str]] = {}
        for unit_id, unit in units.items():
            if not scenario_map.contains(unit.position):
                raise ValueError(f"unit {unit_id} starts outside passable map")
            occupants = occupant_by_hex.setdefault(unit.position, [])
            occupants.append(unit_id)

        for leader_id, leader in leader_lookup.items():
            if not scenario_map.contains(leader.position):
                raise ValueError(f"leader {leader_id} starts outside passable map")

        activation_state = activation or _initial_activation_state(active_side=active_side, leaders=leader_lookup)
        frozen_occupants = {coord: tuple(unit_ids) for coord, unit_ids in occupant_by_hex.items()}

        return cls(
            scenario_map=scenario_map,
            scenario=scenario,
            ruleset=ruleset,
            active_side=active_side,
            units=units,
            leaders=leader_lookup,
            occupant_by_hex=frozen_occupants,
            rng_seed=rng_seed,
            rng_counter=rng_counter,
            turn_number=turn_number,
            turn_phase=turn_phase,
            activation=activation_state,
            open_reaction_windows=open_reaction_windows,
            spent_reaction_windows=spent_reaction_windows,
        )

    def unit_at(self, coord: HexCoord) -> Unit | None:
        """Return first unit occupying coordinate, if any."""

        unit_ids = self.occupant_by_hex.get(coord)
        if not unit_ids:
            return None

        return self.units[unit_ids[0]]

    def units_at(self, coord: HexCoord) -> tuple[Unit, ...]:
        """Return all units occupying coordinate, preserving insertion order."""

        unit_ids = self.occupant_by_hex.get(coord, ())
        return tuple(self.units[unit_id] for unit_id in unit_ids)

    def leaders_at(self, coord: HexCoord) -> tuple[Leader, ...]:
        """Return all leaders currently stacked in one hex."""

        return tuple(leader for leader in self.leaders.values() if leader.position == coord)

    def with_units(self, units: dict[str, Unit]) -> GameState:
        """Return a copy with replaced units dictionary."""

        return GameState.from_units(
            scenario_map=self.scenario_map,
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=units,
            leaders=self.leaders,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            activation=self.activation,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_leaders(self, leaders: dict[str, Leader]) -> GameState:
        """Return a copy with replaced leaders dictionary."""

        return GameState.from_units(
            scenario_map=self.scenario_map,
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            leaders=leaders,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            activation=self.activation,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_active_side(self, active_side: Side) -> GameState:
        """Return a copy with updated active side."""

        return GameState(
            scenario_map=self.scenario_map,
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=active_side,
            units=self.units,
            leaders=self.leaders,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            activation=self.activation,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_rng_counter(self, rng_counter: int) -> GameState:
        """Return copy with updated RNG counter."""

        return GameState(
            scenario_map=self.scenario_map,
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            leaders=self.leaders,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=rng_counter,
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            activation=self.activation,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_turn_phase(self, turn_phase: TurnPhase) -> GameState:
        """Return copy with updated turn phase."""

        return GameState(
            scenario_map=self.scenario_map,
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            leaders=self.leaders,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_number=self.turn_number,
            turn_phase=turn_phase,
            activation=self.activation,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_turn_number(self, turn_number: int) -> GameState:
        """Return copy with updated turn number."""

        return GameState(
            scenario_map=self.scenario_map,
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            leaders=self.leaders,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_number=turn_number,
            turn_phase=self.turn_phase,
            activation=self.activation,
            open_reaction_windows=self.open_reaction_windows,
            spent_reaction_windows=self.spent_reaction_windows,
        )

    def with_activation(self, activation: ActivationState) -> GameState:
        """Return copy with replaced activation context."""

        return GameState(
            scenario_map=self.scenario_map,
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            leaders=self.leaders,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            activation=activation,
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
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            leaders=self.leaders,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            activation=self.activation,
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
            scenario=self.scenario,
            ruleset=self.ruleset,
            active_side=self.active_side,
            units=self.units,
            leaders=self.leaders,
            occupant_by_hex=self.occupant_by_hex,
            rng_seed=self.rng_seed,
            rng_counter=self.rng_counter,
            turn_number=self.turn_number,
            turn_phase=self.turn_phase,
            activation=self.activation,
            open_reaction_windows=next_open_windows,
            spent_reaction_windows=next_spent_windows,
        )

    def active_leaders(self) -> tuple[Leader, ...]:
        """Return leaders for active side sorted by initiative then id."""

        return tuple(
            sorted(
                (leader for leader in self.leaders.values() if leader.side == self.active_side),
                key=lambda leader: (leader.initiative, leader.leader_id),
            )
        )

    def inactive_leaders(self) -> tuple[Leader, ...]:
        """Return leaders on active side still eligible for first activation."""

        return tuple(leader for leader in self.active_leaders() if leader.status == LeaderStatus.INACTIVE)

    def current_active_leader(self) -> Leader | None:
        """Return currently active leader, if any."""

        leader_id = self.activation.leader_id
        if leader_id is None:
            return None
        return self.leaders.get(leader_id)


def _initial_activation_state(active_side: Side, leaders: dict[str, Leader]) -> ActivationState:
    """Build default activation state for one side's first eligible leader."""

    eligible = sorted(
        (leader for leader in leaders.values() if leader.side == active_side),
        key=lambda leader: (leader.initiative, leader.leader_id),
    )
    if not eligible:
        return ActivationState()

    first = eligible[0]
    return ActivationState(
        leader_id=first.leader_id,
        orders_remaining=first.initiative,
        line_commands_remaining=max(0, first.line_command),
    )


def _normalize_leaders(active_side: Side, units: dict[str, Unit], leaders: dict[str, Leader] | None) -> dict[str, Leader]:
    """Return provided leaders or synthesize one for isolated rule-test states."""

    if leaders is not None:
        return leaders

    active_units = sorted(
        (unit for unit in units.values() if unit.side == active_side),
        key=lambda unit: unit.unit_id,
    )
    if not active_units:
        return {}

    anchor = active_units[0]
    return {
        f"{active_side.value}_synthetic_leader": Leader(
            leader_id=f"{active_side.value}_synthetic_leader",
            side=active_side,
            name=f"{active_side.value.title()} Synthetic Leader",
            position=anchor.position,
            is_overall_commander=True,
            initiative=99,
            command_range=99,
            line_command=99,
            strategy=9,
            charisma=0,
            elite_commander=False,
            command_restrictions=(),
            status=LeaderStatus.ACTIVE,
        )
    }
