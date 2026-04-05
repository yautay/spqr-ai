"""Typed AI action containers shared by generator/search modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from legions_api.core.actions import MissileAction, MoveAction, ReloadMissileAction, ShockAction

AIActionType = Literal["move", "missile", "reload", "shock"]


@dataclass(frozen=True, slots=True)
class AICandidateAction:
    """One legal candidate action considered by the AI search."""

    action_type: AIActionType
    action: MoveAction | MissileAction | ReloadMissileAction | ShockAction
    summary: str


@dataclass(frozen=True, slots=True)
class AIScoredCandidate:
    """Candidate action with evaluator score metadata."""

    candidate: AICandidateAction
    score: float


@dataclass(frozen=True, slots=True)
class AISearchResult:
    """Result of bounded AI candidate scoring iteration."""

    selected: AICandidateAction | None
    considered_actions: int
    elapsed_ms: int
    scored_candidates: tuple[AIScoredCandidate, ...]
