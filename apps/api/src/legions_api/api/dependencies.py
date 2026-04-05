"""FastAPI dependency providers."""

from __future__ import annotations

from pathlib import Path

from legions_api.api.event_stream import GameEventStream
from legions_api.api.state_store import GameStateStore
from legions_api.persistence.replay_log import ReplayLog
from legions_api.persistence.snapshots import FileSnapshotRepository, SnapshotRepository

_PERSISTENCE_ROOT = Path(__file__).resolve().parents[5] / ".spqr"

_STORE = GameStateStore()
_EVENT_STREAM = GameEventStream(log_file_path=_PERSISTENCE_ROOT / "events" / "events.jsonl")
_REPLAY_LOG = ReplayLog(log_file_path=_PERSISTENCE_ROOT / "events" / "replay.jsonl")
_SNAPSHOTS: SnapshotRepository = FileSnapshotRepository(_PERSISTENCE_ROOT / "snapshots")


def get_game_store() -> GameStateStore:
    """Return singleton in-memory state store for early development."""

    return _STORE


def get_event_stream() -> GameEventStream:
    """Return singleton in-memory event stream."""

    return _EVENT_STREAM


def get_snapshot_repository() -> SnapshotRepository:
    """Return singleton snapshot repository adapter."""

    return _SNAPSHOTS


def get_replay_log() -> ReplayLog:
    """Return singleton replay-event log."""

    return _REPLAY_LOG
