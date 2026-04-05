"""Leader domain model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from legions_api.core.model.hex import HexCoord
from legions_api.core.model.unit import Side


class LeaderStatus(StrEnum):
    """Leader activation state within current turn."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    FINISHED = "finished"
    BYPASSED = "bypassed"
    TRUMPED = "trumped"


@dataclass(frozen=True, slots=True)
class Leader:
    """Command-capable battlefield leader."""

    leader_id: str
    side: Side
    name: str
    position: HexCoord
    is_overall_commander: bool = False
    initiative: int = 0
    command_range: int = 0
    line_command: int = 0
    strategy: int = 0
    charisma: int = 0
    elite_commander: bool = False
    command_restrictions: tuple[str, ...] = ()
    status: LeaderStatus = LeaderStatus.INACTIVE

    def with_status(self, status: LeaderStatus) -> Leader:
        """Return leader with updated activation status."""

        return Leader(
            leader_id=self.leader_id,
            side=self.side,
            name=self.name,
            position=self.position,
            is_overall_commander=self.is_overall_commander,
            initiative=self.initiative,
            command_range=self.command_range,
            line_command=self.line_command,
            strategy=self.strategy,
            charisma=self.charisma,
            elite_commander=self.elite_commander,
            command_restrictions=self.command_restrictions,
            status=status,
        )

    def with_position(self, position: HexCoord) -> Leader:
        """Return leader moved to another hex."""

        return Leader(
            leader_id=self.leader_id,
            side=self.side,
            name=self.name,
            position=position,
            is_overall_commander=self.is_overall_commander,
            initiative=self.initiative,
            command_range=self.command_range,
            line_command=self.line_command,
            strategy=self.strategy,
            charisma=self.charisma,
            elite_commander=self.elite_commander,
            command_restrictions=self.command_restrictions,
            status=self.status,
        )
