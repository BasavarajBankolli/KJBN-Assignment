"""Food truck search routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_food_truck_service
from app.schemas.api import FoodTruckListResponse
from app.schemas.query import FoodTruckSearchParams
from app.services.food_trucks import FoodTruckService

router = APIRouter(tags=["food-trucks"])


@router.get("/food-trucks", response_model=FoodTruckListResponse)
async def list_food_trucks(
    lat: Annotated[str | None, Query(description="Search center latitude (-90 to 90).")] = None,
    lng: Annotated[str | None, Query(description="Search center longitude (-180 to 180).")] = None,
    radius: Annotated[
        str | None,
        Query(description="Search radius in kilometers (0.1 to 50). Defaults to 2."),
    ] = None,
    food_type: Annotated[str | None, Query(description="Filter by food type, e.g. 'tacos'.")] = None,
    search: Annotated[
        str | None,
        Query(description="Free-text search across vendor, address, and food items."),
    ] = None,
    limit: Annotated[str | None, Query(description="Page size (1 to 100). Defaults to 20.")] = None,
    offset: Annotated[str | None, Query(description="Page offset. Defaults to 0.")] = None,
    service: FoodTruckService = Depends(get_food_truck_service),
) -> FoodTruckListResponse:
    """Search food trucks near a geographic location.

    Coordinates are required; radius, filters, and pagination are optional.
    Results are sorted by distance from the search center, nearest first.
    """
    params = FoodTruckSearchParams.from_query(
        lat=lat,
        lng=lng,
        radius=radius,
        food_type=food_type,
        search=search,
        limit=limit,
        offset=offset,
    )
    return await service.search(params)