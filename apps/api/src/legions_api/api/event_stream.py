"""In-memory pub/sub stream for game events."""

from __future__ import annotations

import json
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Lock

from legions_api.api.schemas import GameEventPayload


class GameEventStream:
    """Thread-safe in-memory fan-out stream for websocket subscribers."""

    def __init__(self, max_queue_size: int = 256, log_file_path: Path | None = None) -> None:
        self._max_queue_size = max_queue_size
        self._lock = Lock()
        self._subscribers: set[Queue[GameEventPayload]] = set()
        self._history: list[GameEventPayload] = []
        self._log_file_path = log_file_path
        if self._log_file_path is not None:
            self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
            if self._log_file_path.exists():
                for line in self._log_file_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    payload = json.loads(line)
                    if not isinstance(payload, dict):
                        continue
                    self._history.append(GameEventPayload.model_validate(payload))

    def subscribe(self) -> Queue[GameEventPayload]:
        """Register one subscriber and return its queue."""

        queue: Queue[GameEventPayload] = Queue(maxsize=self._max_queue_size)
        with self._lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: Queue[GameEventPayload]) -> None:
        """Remove subscriber queue if currently registered."""

        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: GameEventPayload) -> None:
        """Publish one event to all active subscribers."""

        with self._lock:
            subscribers = tuple(self._subscribers)
            self._history.append(event)
            if self._log_file_path is not None:
                with self._log_file_path.open("a", encoding="utf-8") as file_obj:
                    file_obj.write(json.dumps(event.model_dump(mode="json"), sort_keys=True))
                    file_obj.write("\n")

        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except Full:
                try:
                    queue.get_nowait()
                except Empty:
                    pass

                try:
                    queue.put_nowait(event)
                except Full:
                    continue

    def history(self, start_offset: int = 0) -> tuple[GameEventPayload, ...]:
        """Return immutable event history from selected offset."""

        with self._lock:
            return tuple(self._history[start_offset:])

    def total_events(self) -> int:
        """Return number of events in ordered history."""

        with self._lock:
            return len(self._history)

    def clear_history(self) -> None:
        """Clear in-memory and file-backed event history."""

        with self._lock:
            self._history = []
            if self._log_file_path is not None:
                self._log_file_path.write_text("", encoding="utf-8")
