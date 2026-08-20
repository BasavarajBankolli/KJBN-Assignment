"""Food truck business logic: distance, radius, search, sorting, pagination.

The service coordinates the DataSF client with in-process, fully tested
logic. Data flows: route -> service -> DataSF client -> normalized trucks
-> filtered/sorted/paginated API response.
"""

import logging
import math

from app.clients.datasf import DATASF_APPROVED_STATUS, DataSFClient
from app.core.cache import TTLCache
from app.schemas.api import Coordinates, FoodTruckListResponse, FoodTruckResponse
from app.schemas.food_truck import FoodTruck
from app.schemas.query import FoodTruckSearchParams

logger = logging.getLogger(__name__)

#: Mean Earth radius in meters (IUGG).
EARTH_RADIUS_M = 6_371_000.0


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two WGS84 points (Haversine formula)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _contains(haystack: str | None, needle: str) -> bool:
    """Case-insensitive substring check that tolerates None values."""
    return needle in (haystack or "").lower()


class FoodTruckService:
    """Application service orchestrating DataSF retrieval and search logic.

    Caching is applied to the upstream DataSF fetch, keyed by the
    parameters that affect the upstream result (the permit ``status``
    filter). Radius, search, and pagination parameters are applied
    in-process and therefore do not affect the cached upstream payload.
    """

    def __init__(
        self,
        client: DataSFClient,
        cache: TTLCache[list[FoodTruck]] | None = None,
    ) -> None:
        self._client = client
        self._cache = cache

    async def search(self, params: FoodTruckSearchParams) -> FoodTruckListResponse:
        """Search food trucks near the requested location.

        Fetches the source dataset through the DataSF client (cached),
        then filters by radius, search text, and food type, sorts
        nearest-first, and paginates.
        """
        trucks = await self._get_all_trucks()
        return self.filter_and_paginate(trucks, params)

    async def _get_all_trucks(self, status: str = DATASF_APPROVED_STATUS) -> list[FoodTruck]:
        """Fetch the full truck list, serving repeat requests from cache."""
        if self._cache is None or not self._cache.enabled:
            return await self._client.fetch_food_trucks(status=status)

        key = self._cache_key(status)
        cached = self._cache.get(key)
        if cached is not None:
            logger.info("Cache hit for %s (%d trucks)", key, len(cached))
            return cached

        logger.info("Cache miss for %s - fetching from DataSF", key)
        trucks = await self._client.fetch_food_trucks(status=status)
        self._cache.set(key, trucks)
        return trucks

    @staticmethod
    def _cache_key(status: str) -> str:
        """Canonical cache key for an upstream fetch.

        Includes every parameter that affects the upstream result; extend
        here if more upstream query parameters are introduced.
        """
        return f"datasf:food_trucks:status={status}"

    def filter_and_paginate(
        self, trucks: list[FoodTruck], params: FoodTruckSearchParams
    ) -> FoodTruckListResponse:
        """Pure, synchronous pipeline - easily unit tested without I/O."""
        radius_m = params.radius_km * 1000.0
        query = (params.search or "").lower()
        food_type = (params.food_type or "").lower()

        results: list[FoodTruckResponse] = []
        for truck in trucks:
            if truck.latitude is None or truck.longitude is None:
                # Ungeocoded permits cannot be placed on a map.
                continue

            distance_m = haversine_distance_m(
                params.lat, params.lng, truck.latitude, truck.longitude
            )
            if distance_m > radius_m:
                continue
            if food_type and not _contains(truck.food_items, food_type):
                continue
            if query and not (
                _contains(truck.applicant, query)
                or _contains(truck.address, query)
                or _contains(truck.location_description, query)
                or _contains(truck.food_items, query)
            ):
                continue

            results.append(
                FoodTruckResponse(
                    id=truck.id,
                    applicant=truck.applicant,
                    facility_type=truck.facility_type,
                    location_description=truck.location_description,
                    address=truck.address,
                    food_items=truck.food_items,
                    latitude=truck.latitude,
                    longitude=truck.longitude,
                    distance_m=distance_m,
                )
            )

        # Nearest first; id as a deterministic tie-breaker.
        results.sort(key=lambda truck: (truck.distance_m, truck.id))

        total = len(results)
        page = results[params.offset : params.offset + params.limit]

        logger.info(
            "Food truck search: %d within %.1f km, %d after filters, returning %d",
            len(trucks),
            params.radius_km,
            total,
            len(page),
        )
        return FoodTruckListResponse(
            trucks=page,
            total=total,
            limit=params.limit,
            offset=params.offset,
            center=Coordinates(latitude=params.lat, longitude=params.lng),
            radius_km=params.radius_km,
        )