"""Persistence adapters and snapshot codecs."""

from legions_api.persistence.replay_log import ReplayEvent, ReplayLog
from legions_api.persistence.snapshots import FileSnapshotRepository, InMemorySnapshotRepository, SnapshotRecord, SnapshotRepository
from legions_api.persistence.state_codec import decode_state, encode_state

__all__ = [
    "FileSnapshotRepository",
    "InMemorySnapshotRepository",
    "ReplayEvent",
    "ReplayLog",
    "SnapshotRecord",
    "SnapshotRepository",
    "decode_state",
    "encode_state",
]
