"""Stable API response schemas exposed to clients.

These models define the public contract of the API and are deliberately
decoupled from both the raw DataSF payload and the internal domain model.
"""

from pydantic import BaseModel


class Coordinates(BaseModel):
    """A geographic point."""

    latitude: float
    longitude: float


class FoodTruckResponse(BaseModel):
    """A food truck in API responses, including its distance from the search center."""

    id: str
    applicant: str
    facility_type: str | None = None
    location_description: str | None = None
    address: str | None = None
    food_items: str | None = None
    latitude: float
    longitude: float
    distance_m: float


class FoodTruckListResponse(BaseModel):
    """Paginated food truck search results."""

    trucks: list[FoodTruckResponse]
    total: int
    limit: int
    offset: int
    center: Coordinates
    radius_km: float