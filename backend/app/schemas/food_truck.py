"""Internal normalized food truck model.

This is the canonical representation used by the application. It is
deliberately decoupled from the raw DataSF payload shape so the external
API can change without leaking into our domain or our API responses.
"""

from pydantic import BaseModel


class FoodTruck(BaseModel):
    """A single food truck (permit holder) at a geographic location."""

    id: str
    applicant: str
    facility_type: str | None = None
    location_description: str | None = None
    address: str | None = None
    permit: str | None = None
    status: str | None = None
    food_items: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    schedule_url: str | None = None