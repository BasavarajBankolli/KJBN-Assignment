"""Tests for the in-process TTL cache."""

import pytest

from app.core.cache import TTLCache


class FakeClock:
    """Deterministic monotonic clock for expiration tests."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_set_and_get_roundtrip() -> None:
    cache = TTLCache[str](ttl_seconds=60)

    cache.set("a", "value-a")

    assert cache.get("a") == "value-a"
    assert len(cache) == 1


def test_miss_returns_none() -> None:
    cache = TTLCache[str](ttl_seconds=60)

    assert cache.get("missing") is None


def test_entry_expires_after_ttl() -> None:
    clock = FakeClock()
    cache = TTLCache[str](ttl_seconds=5, now_fn=clock)

    cache.set("a", "v")

    clock.advance(4.999)
    assert cache.get("a") == "v"  # just before expiry

    clock.advance(0.001)  # now exactly at the TTL boundary
    assert cache.get("a") is None  # entry is expired


def test_expired_entries_are_evicted_on_access() -> None:
    clock = FakeClock()
    cache = TTLCache[str](ttl_seconds=5, now_fn=clock)

    cache.set("a", "v")
    clock.advance(10)
    cache.get("a")

    assert len(cache) == 0


def test_distinct_keys_do_not_collide() -> None:
    cache = TTLCache[str](ttl_seconds=60)

    cache.set("key:1", "one")
    cache.set("key:2", "two")

    assert cache.get("key:1") == "one"
    assert cache.get("key:2") == "two"


def test_ttl_zero_disables_caching() -> None:
    cache = TTLCache[str](ttl_seconds=0)

    assert cache.enabled is False
    cache.set("a", "v")

    assert cache.get("a") is None
    assert len(cache) == 0


def test_negative_ttl_rejected() -> None:
    with pytest.raises(ValueError):
        TTLCache[str](ttl_seconds=-1)


def test_clear_empties_cache() -> None:
    cache = TTLCache[str](ttl_seconds=60)

    cache.set("a", "v")
    cache.clear()

    assert cache.get("a") is None
    assert len(cache) == 0


def test_overwrite_refreshes_value_and_ttl() -> None:
    clock = FakeClock()
    cache = TTLCache[str](ttl_seconds=10, now_fn=clock)

    cache.set("a", "old")
    clock.advance(6)
    cache.set("a", "new")

    assert cache.get("a") == "new"
    clock.advance(6)  # 12s after first set, 6s after refresh
    assert cache.get("a") == "new"


def test_holds_list_values() -> None:
    cache = TTLCache[list[str]](ttl_seconds=60)

    cache.set("k", ["a", "b"])

    assert cache.get("k") == ["a", "b"]