"""In-memory pub/sub stream for game events."""

from __future__ import annotations

from queue import Empty, Full, Queue
from threading import Lock

from legions_api.api.schemas import GameEventPayload


class GameEventStream:
    """Thread-safe in-memory fan-out stream for websocket subscribers."""

    def __init__(self, max_queue_size: int = 256) -> None:
        self._max_queue_size = max_queue_size
        self._lock = Lock()
        self._subscribers: set[Queue[GameEventPayload]] = set()

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
