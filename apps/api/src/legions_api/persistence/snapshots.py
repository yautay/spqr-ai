"""Snapshot persistence adapters for save/load API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Protocol

from legions_api.core.model.game_state import GameState
from legions_api.persistence.state_codec import decode_state, encode_state


@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    """One persisted game snapshot with event offset metadata."""

    slot_id: str
    saved_at: str
    event_offset: int
    state: GameState


class SnapshotRepository(Protocol):
    """Interface for snapshot storage adapters."""

    def save(self, slot_id: str, state: GameState, event_offset: int) -> SnapshotRecord:
        """Persist snapshot and return stored metadata."""

    def load(self, slot_id: str) -> SnapshotRecord | None:
        """Load snapshot by slot id."""

    def list_snapshots(self) -> tuple[SnapshotRecord, ...]:
        """List all snapshot slots sorted by recency."""


class InMemorySnapshotRepository:
    """Thread-safe in-memory snapshot adapter for tests and local runs."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_slot: dict[str, SnapshotRecord] = {}

    def save(self, slot_id: str, state: GameState, event_offset: int) -> SnapshotRecord:
        """Store snapshot in memory."""

        record = SnapshotRecord(
            slot_id=slot_id,
            saved_at=datetime.now(tz=UTC).isoformat(),
            event_offset=event_offset,
            state=state,
        )
        with self._lock:
            self._by_slot[slot_id] = record
        return record

    def load(self, slot_id: str) -> SnapshotRecord | None:
        """Load snapshot from memory by slot id."""

        with self._lock:
            return self._by_slot.get(slot_id)

    def list_snapshots(self) -> tuple[SnapshotRecord, ...]:
        """Return all in-memory snapshots sorted newest-first."""

        with self._lock:
            snapshots = tuple(self._by_slot.values())
        return tuple(sorted(snapshots, key=lambda snapshot: snapshot.saved_at, reverse=True))


class FileSnapshotRepository:
    """File-backed snapshot adapter storing one JSON file per slot."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def save(self, slot_id: str, state: GameState, event_offset: int) -> SnapshotRecord:
        """Serialize and persist one snapshot under selected slot."""

        safe_slot = _normalize_slot(slot_id)
        record = SnapshotRecord(
            slot_id=safe_slot,
            saved_at=datetime.now(tz=UTC).isoformat(),
            event_offset=event_offset,
            state=state,
        )
        payload = {
            "slot_id": record.slot_id,
            "saved_at": record.saved_at,
            "event_offset": record.event_offset,
            "state": encode_state(record.state),
        }
        with self._lock:
            self._slot_path(safe_slot).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return record

    def load(self, slot_id: str) -> SnapshotRecord | None:
        """Read snapshot JSON by slot id if present."""

        safe_slot = _normalize_slot(slot_id)
        path = self._slot_path(safe_slot)
        if not path.exists():
            return None

        with self._lock:
            payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("snapshot file must contain object payload")

        return SnapshotRecord(
            slot_id=str(payload["slot_id"]),
            saved_at=str(payload["saved_at"]),
            event_offset=int(payload.get("event_offset", 0)),
            state=decode_state(_as_dict(payload["state"])),
        )

    def list_snapshots(self) -> tuple[SnapshotRecord, ...]:
        """Load all snapshots from storage sorted newest-first."""

        records: list[SnapshotRecord] = []
        with self._lock:
            paths = sorted(self._base_dir.glob("*.json"))
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            records.append(
                SnapshotRecord(
                    slot_id=str(payload["slot_id"]),
                    saved_at=str(payload["saved_at"]),
                    event_offset=int(payload.get("event_offset", 0)),
                    state=decode_state(_as_dict(payload["state"])),
                )
            )

        return tuple(sorted(records, key=lambda snapshot: snapshot.saved_at, reverse=True))

    def _slot_path(self, slot_id: str) -> Path:
        """Resolve file path for one snapshot slot id."""

        return self._base_dir / f"{slot_id}.json"


def _normalize_slot(slot_id: str) -> str:
    """Normalize slot id to filesystem-safe deterministic value."""

    normalized = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in slot_id.strip())
    if not normalized:
        return "quicksave"
    return normalized


def _as_dict(value: object) -> dict[str, object]:
    """Cast unknown payload to object dictionary."""

    if not isinstance(value, dict):
        raise ValueError("expected object payload")
    return value
