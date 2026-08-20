"""Async HTTP client for the DataSF Mobile Food Facility Permit dataset.

The DataSF endpoint is a Socrata SODA API. Notable quirks handled here:

- every field is serialized as a string, including numbers;
- some rows have no latitude/longitude (ungeocoded permits);
- optional fields are simply absent from the JSON payload;
- ``:@computed_region_*`` fields are SDK metadata and must be ignored;
- the API returns a JSON error object (not a list) on failure.

This module is the only place that talks to DataSF. Callers receive
normalized ``FoodTruck`` models, never the raw payload.
"""

import logging

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.exceptions.errors import (
    DataSFHttpError,
    DataSFInvalidResponseError,
    DataSFTimeoutError,
    DataSFUnavailableError,
)
from app.schemas.food_truck import FoodTruck

logger = logging.getLogger(__name__)

#: Socrata hard limit on the number of rows returned per request.
DATASF_MAX_LIMIT = 50_000
#: Default permit status filter - only currently approved (operating) trucks.
DATASF_APPROVED_STATUS = "APPROVED"


class DataSFRawFoodTruck(BaseModel):
    """Raw record shape as returned by the DataSF SODA API.

    Everything except the fields we care about is ignored, including the
    ``:@computed_region_*`` metadata columns.
    """

    model_config = ConfigDict(extra="ignore")

    objectid: str | int
    applicant: str | None = None
    facilitytype: str | None = None
    locationdescription: str | None = None
    address: str | None = None
    permit: str | None = None
    status: str | None = None
    fooditems: str | None = None
    latitude: str | float | None = None
    longitude: str | float | None = None
    schedule: str | None = None


def _to_optional_float(value: str | float | None) -> float | None:
    """Coerce a DataSF numeric string to float, tolerating junk/empty values."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("Ignoring non-numeric coordinate value %r", value)
        return None


def normalize_truck(raw: DataSFRawFoodTruck) -> FoodTruck:
    """Convert a raw DataSF record into the internal normalized model."""
    return FoodTruck(
        id=str(raw.objectid),
        applicant=raw.applicant or "Unknown vendor",
        facility_type=raw.facilitytype,
        location_description=raw.locationdescription,
        address=raw.address,
        permit=raw.permit,
        status=raw.status,
        food_items=raw.fooditems,
        latitude=_to_optional_float(raw.latitude),
        longitude=_to_optional_float(raw.longitude),
        schedule_url=raw.schedule,
    )


class DataSFClient:
    """Async client for the DataSF food trucks dataset.

    An ``httpx.AsyncClient`` is created internally unless one is injected,
    which keeps the client easily testable.
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout_seconds)

    async def aclose(self) -> None:
        """Release the underlying HTTP client."""
        await self._http_client.aclose()

    async def fetch_food_trucks(
        self,
        status: str = DATASF_APPROVED_STATUS,
    ) -> list[FoodTruck]:
        """Fetch and normalize food trucks from DataSF.

        Raises:
            DataSFTimeoutError: the upstream request timed out.
            DataSFUnavailableError: transport failure or non-success status.
            DataSFInvalidResponseError: response body was not a list of records.
        """
        params = {
            "$limit": str(DATASF_MAX_LIMIT),
            "$where": f"status='{status}'",
        }
        logger.info("Fetching food trucks from DataSF (status=%s)", status)

        try:
            response = await self._http_client.get(self._base_url, params=params)
        except httpx.TimeoutException as exc:
            logger.error("DataSF request timed out after %ss", self._timeout_seconds)
            raise DataSFTimeoutError() from exc
        except httpx.HTTPError as exc:
            logger.error("DataSF request failed: %s", exc)
            raise DataSFUnavailableError() from exc

        if response.status_code != httpx.codes.OK:
            detail = f"The DataSF service returned HTTP {response.status_code}."
            try:
                body = response.json()
                if isinstance(body, dict) and body.get("message"):
                    detail = f"The DataSF service returned HTTP {response.status_code}: {body['message']}"
            except ValueError:
                pass
            logger.error("DataSF returned non-OK status: %s", detail)
            raise DataSFHttpError(status_code=response.status_code, detail=detail)

        try:
            payload = response.json()
        except ValueError as exc:
            logger.error("DataSF response was not valid JSON")
            raise DataSFInvalidResponseError() from exc

        if not isinstance(payload, list):
            logger.error("DataSF response was not a JSON list")
            raise DataSFInvalidResponseError()

        trucks: list[FoodTruck] = []
        for index, item in enumerate(payload):
            try:
                raw = DataSFRawFoodTruck.model_validate(item)
            except ValidationError as exc:
                logger.warning("Skipping malformed DataSF record at index %s: %s", index, exc)
                continue
            trucks.append(normalize_truck(raw))

        logger.info("Normalized %d food trucks from DataSF", len(trucks))
        return trucks


def create_datasf_client(base_url: str, timeout_seconds: float) -> DataSFClient:
    """Factory for a configured DataSF client."""
    return DataSFClient(base_url=base_url, timeout_seconds=timeout_seconds)