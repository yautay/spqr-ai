"""Deterministic random helpers used by core rules."""

from __future__ import annotations


def seeded_d10_roll(rng_seed: int, rng_counter: int) -> int:
    """Return deterministic seeded d10 roll for current game RNG state."""

    value = (1664525 * rng_seed + 1013904223 * rng_counter) % (2**32)
    return (value % 10) + 1
