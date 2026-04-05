"""Replay event log adapters used for deterministic reconstruction."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from threading import Lock


@dataclass(frozen=True, slots=True)
class ReplayEvent:
    """One deterministic replay event with transport payload."""

    event_type: str
    payload: dict[str, object]


class ReplayLog:
    """Thread-safe replay event log with optional file persistence."""

    def __init__(self, log_file_path: Path | None = None) -> None:
        self._lock = Lock()
        self._events: list[ReplayEvent] = []
        self._log_file_path = log_file_path
        if self._log_file_path is not None:
            self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
            if self._log_file_path.exists():
                for line in self._log_file_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        continue
                    event_type = raw.get("event_type")
                    payload = raw.get("payload")
                    if not isinstance(event_type, str) or not isinstance(payload, dict):
                        continue
                    self._events.append(ReplayEvent(event_type=event_type, payload=payload))

    def append(self, event: ReplayEvent) -> None:
        """Append one event to ordered replay log."""

        with self._lock:
            self._events.append(event)
            if self._log_file_path is not None:
                with self._log_file_path.open("a", encoding="utf-8") as file_obj:
                    file_obj.write(json.dumps({"event_type": event.event_type, "payload": event.payload}, sort_keys=True))
                    file_obj.write("\n")

    def events(self, start_offset: int = 0) -> tuple[ReplayEvent, ...]:
        """Return replay events from selected offset."""

        with self._lock:
            return tuple(self._events[start_offset:])

    def total_events(self) -> int:
        """Return replay event count."""

        with self._lock:
            return len(self._events)

    def clear(self) -> None:
        """Clear replay events from memory and optional file."""

        with self._lock:
            self._events = []
            if self._log_file_path is not None:
                self._log_file_path.write_text("", encoding="utf-8")
