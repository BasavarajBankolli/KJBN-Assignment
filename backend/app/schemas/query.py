"""Validated query parameters for the food trucks search endpoint.

Query values arrive from HTTP as raw strings; ``FoodTruckSearchParams``
parses and validates them, raising the application's consistent error
types (``INVALID_LOCATION``, ``INVALID_RADIUS``, ``INVALID_PAGINATION``)
instead of framework default 422 responses.
"""

from pydantic import BaseModel

from app.exceptions.errors import (
    InvalidLocationError,
    InvalidPaginationError,
    InvalidRadiusError,
)

#: Default search radius in kilometers.
DEFAULT_RADIUS_KM = 2.0
#: Allowed search radius bounds in kilometers (inclusive).
MIN_RADIUS_KM = 0.1
MAX_RADIUS_KM = 50.0

#: Default and maximum page size.
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MIN_LIMIT = 1

#: Minimum (and default) offset.
DEFAULT_OFFSET = 0
MIN_OFFSET = 0


def _clean(value: str | None) -> str | None:
    """Trim a raw query value; empty strings become None."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class FoodTruckSearchParams(BaseModel):
    """Normalized, validated search parameters for the food trucks endpoint."""

    lat: float
    lng: float
    radius_km: float = DEFAULT_RADIUS_KM
    food_type: str | None = None
    search: str | None = None
    limit: int = DEFAULT_LIMIT
    offset: int = DEFAULT_OFFSET

    @classmethod
    def from_query(
        cls,
        *,
        lat: str | None,
        lng: str | None,
        radius: str | None = None,
        food_type: str | None = None,
        search: str | None = None,
        limit: str | None = None,
        offset: str | None = None,
    ) -> "FoodTruckSearchParams":
        """Parse and validate raw HTTP query parameters.

        Raises:
            InvalidLocationError: missing/non-numeric/out-of-range coordinates.
            InvalidRadiusError: radius outside the allowed bounds.
            InvalidPaginationError: limit/offset outside the allowed bounds.
        """
        if lat is None or lng is None:
            raise InvalidLocationError(
                detail="Both 'lat' and 'lng' query parameters are required."
            )

        try:
            latitude = float(lat)
            longitude = float(lng)
        except ValueError as exc:
            raise InvalidLocationError(
                detail="'lat' and 'lng' must be decimal numbers."
            ) from exc

        if not -90.0 <= latitude <= 90.0:
            raise InvalidLocationError(detail="Latitude must be between -90 and 90.")
        if not -180.0 <= longitude <= 180.0:
            raise InvalidLocationError(detail="Longitude must be between -180 and 180.")

        radius_km = DEFAULT_RADIUS_KM
        if _clean(radius) is not None:
            try:
                radius_km = float(radius)
            except ValueError as exc:
                raise InvalidRadiusError(
                    detail="'radius' must be a number of kilometers."
                ) from exc
            if not MIN_RADIUS_KM <= radius_km <= MAX_RADIUS_KM:
                raise InvalidRadiusError(
                    detail=f"'radius' must be between {MIN_RADIUS_KM} and {MAX_RADIUS_KM} km."
                )

        page_limit = DEFAULT_LIMIT
        if _clean(limit) is not None:
            try:
                page_limit = int(limit)
            except ValueError as exc:
                raise InvalidPaginationError(
                    detail="'limit' must be an integer."
                ) from exc
            if not MIN_LIMIT <= page_limit <= MAX_LIMIT:
                raise InvalidPaginationError(
                    detail=f"'limit' must be between {MIN_LIMIT} and {MAX_LIMIT}."
                )

        page_offset = DEFAULT_OFFSET
        if _clean(offset) is not None:
            try:
                page_offset = int(offset)
            except ValueError as exc:
                raise InvalidPaginationError(
                    detail="'offset' must be an integer."
                ) from exc
            if page_offset < MIN_OFFSET:
                raise InvalidPaginationError(
                    detail="'offset' must be zero or greater."
                )

        return cls(
            lat=latitude,
            lng=longitude,
            radius_km=radius_km,
            food_type=_clean(food_type),
            search=_clean(search),
            limit=page_limit,
            offset=page_offset,
        )