"""Deterministic RNG helper tests."""

from legions_api.core.random import seeded_d10_roll


def test_seeded_d10_roll_is_stable_for_same_seed_and_counter() -> None:
    """RNG helper should return same value for same input pair."""

    assert seeded_d10_roll(rng_seed=1, rng_counter=0) == seeded_d10_roll(rng_seed=1, rng_counter=0)


def test_seeded_d10_roll_advances_when_counter_changes() -> None:
    """RNG helper should generate sequence values in 1-10 range."""

    sequence = [seeded_d10_roll(rng_seed=1, rng_counter=index) for index in range(6)]

    assert sequence == [6, 9, 2, 5, 8, 5]
