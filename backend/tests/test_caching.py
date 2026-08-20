"""Tests for caching behavior in the food truck service.

Uses an in-memory stub client so no network or respx machinery is needed.
"""

from app.core.cache import TTLCache
from app.schemas.query import FoodTruckSearchParams
from app.services.food_trucks import FoodTruckService
from tests.mock_data import ALL_TRUCKS, CENTER_LAT, CENTER_LNG


class StubDataSFClient:
    """In-memory stand-in for DataSFClient that records fetch calls."""

    def __init__(self, trucks: list | None = None) -> None:
        self.trucks = trucks or ALL_TRUCKS
        self.calls: list[str] = []

    async def fetch_food_trucks(self, status: str = "APPROVED") -> list:
        self.calls.append(status)
        return list(self.trucks)

    async def aclose(self) -> None:
        pass


class FakeClock:
    """Deterministic monotonic clock for cache expiration tests."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_params(**overrides: float | str | None) -> FoodTruckSearchParams:
    return FoodTruckSearchParams(lat=CENTER_LAT, lng=CENTER_LNG, **overrides)


async def test_cache_miss_fetches_and_stores() -> None:
    client = StubDataSFClient()
    cache = TTLCache[list](ttl_seconds=60)
    service = FoodTruckService(client=client, cache=cache)

    await service.search(make_params())

    assert len(client.calls) == 1
    assert len(cache) == 1


async def test_cache_hit_skips_upstream_fetch() -> None:
    client = StubDataSFClient()
    cache = TTLCache[list](ttl_seconds=60)
    service = FoodTruckService(client=client, cache=cache)

    first = await service.search(make_params())
    # Different search/radius params reuse the cached upstream payload,
    # since those parameters are applied in-process, not upstream.
    second = await service.search(make_params(radius_km=5.0, search="golden"))

    assert first.total == 2
    assert second.total == 1
    assert len(client.calls) == 1


async def test_cache_expiration_triggers_refetch() -> None:
    clock = FakeClock()
    client = StubDataSFClient()
    cache = TTLCache[list](ttl_seconds=10, now_fn=clock)
    service = FoodTruckService(client=client, cache=cache)

    await service.search(make_params())
    clock.advance(10.001)
    await service.search(make_params())

    assert len(client.calls) == 2


async def test_disabled_cache_fetches_every_time() -> None:
    client = StubDataSFClient()
    cache = TTLCache[list](ttl_seconds=0)
    service = FoodTruckService(client=client, cache=cache)

    await service.search(make_params())
    await service.search(make_params())

    assert len(client.calls) == 2


async def test_no_cache_instance_fetches_every_time() -> None:
    client = StubDataSFClient()
    service = FoodTruckService(client=client)

    await service.search(make_params())
    await service.search(make_params())

    assert len(client.calls) == 2


def test_cache_key_includes_status() -> None:
    approved = FoodTruckService._cache_key("APPROVED")
    requested = FoodTruckService._cache_key("REQUESTED")

    assert approved == "datasf:food_trucks:status=APPROVED"
    assert approved != requested


async def test_different_statuses_have_distinct_cache_entries() -> None:
    client = StubDataSFClient()
    cache = TTLCache[list](ttl_seconds=60)
    service = FoodTruckService(client=client, cache=cache)

    await service._get_all_trucks(status="APPROVED")
    await service._get_all_trucks(status="APPROVED")
    await service._get_all_trucks(status="REQUESTED")

    assert len(client.calls) == 2
    assert len(cache) == 2