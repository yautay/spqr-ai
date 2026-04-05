"""Scenario-specific runtime metadata."""

from __future__ import annotations

from dataclasses import dataclass, field

from legions_api.core.model.unit import Side


@dataclass(frozen=True, slots=True)
class LineEligibilityFilter:
    """Unit filters that define one legal line-command cohort."""

    unit_types: tuple[str, ...] = ()
    unit_classes: tuple[str, ...] = ()
    allow_velites_skirmish_interruption: bool = False


@dataclass(frozen=True, slots=True)
class LineAdjacencyRule:
    """Spacing constraints for line-command eligibility."""

    max_gap: int = 0
    allow_gap_through: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LineCommandRule:
    """One scenario line-command eligibility rule."""

    line_id: str
    side: Side
    eligible_unit_filters: LineEligibilityFilter = field(default_factory=LineEligibilityFilter)
    adjacency_rule: LineAdjacencyRule = field(default_factory=LineAdjacencyRule)
    requires_same_orientation: bool = True
    max_lines_per_command: int = 1


@dataclass(frozen=True, slots=True)
class SpecialRules:
    """Scenario-level optional or faction-specific rule toggles."""

    carthaginian_command_override: bool = False
    triarii_doctrine_active: bool = False
    double_depth_phalanx_allowed: bool = False
    pre_arranged_withdrawal_available: bool = False
    elephant_command_optional_active: bool = False
    engaged_optional_active: bool = False
    artillery_active: bool = False


@dataclass(frozen=True, slots=True)
class RoutPointRules:
    """Scenario withdrawal accounting metadata."""

    default_formula: str = "unit_tq"
    overrides: dict[str, str] = field(default_factory=dict)
    named_multiplier: int = 5
    tribune_prefect_replacement: str = "initiative"


@dataclass(frozen=True, slots=True)
class VictoryRules:
    """Scenario withdrawal and retreat-edge configuration."""

    retreat_edges: dict[Side, str] = field(default_factory=dict)
    withdrawal_levels: dict[Side, int] = field(default_factory=dict)
    rout_point_rules: RoutPointRules = field(default_factory=RoutPointRules)


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    """Runtime container for scenario-bound rules metadata."""

    line_command_rules: tuple[LineCommandRule, ...] = ()
    special_rules: SpecialRules = field(default_factory=SpecialRules)
    victory_rules: VictoryRules = field(default_factory=VictoryRules)
