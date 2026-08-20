"""Unit tests for the food truck service layer (pure logic, no network)."""

import pytest

from app.exceptions.errors import (
    InvalidLocationError,
    InvalidPaginationError,
    InvalidRadiusError,
)
from app.schemas.api import FoodTruckListResponse
from app.schemas.query import FoodTruckSearchParams
from app.services.food_trucks import FoodTruckService, haversine_distance_m
from tests.mock_data import (
    ALL_TRUCKS,
    CENTER_LAT,
    CENTER_LNG,
    TRUCK_A,
    TRUCK_B,
    TRUCK_C,
    TRUCK_NO_COORDS,
)


def make_service() -> FoodTruckService:
    return FoodTruckService(client=None)  # type: ignore[arg-type]


def search(trucks: list, **overrides) -> FoodTruckListResponse:
    params = FoodTruckSearchParams(lat=CENTER_LAT, lng=CENTER_LNG, **overrides)
    return make_service().filter_and_paginate(trucks, params)


# ---------------------------------------------------------------------------
# Haversine distance
# ---------------------------------------------------------------------------


def test_haversine_zero_for_same_point() -> None:
    assert haversine_distance_m(37.7793, -122.4193, 37.7793, -122.4193) == 0.0


def test_haversine_equator_longitude_degree() -> None:
    # One degree of longitude at the equator is ~111.19 km.
    distance = haversine_distance_m(0.0, 0.0, 0.0, 1.0)
    assert distance == pytest.approx(111_195.0, rel=0.001)


def test_haversine_meridian_degree() -> None:
    # One degree of latitude on a spherical Earth (R = 6371 km) is ~111.19 km.
    distance = haversine_distance_m(0.0, 0.0, 1.0, 0.0)
    assert distance == pytest.approx(111_195.0, rel=0.001)


def test_haversine_is_symmetric() -> None:
    forward = haversine_distance_m(37.7793, -122.4193, 37.7683, -122.4193)
    backward = haversine_distance_m(37.7683, -122.4193, 37.7793, -122.4193)
    assert forward == pytest.approx(backward, rel=0.001)


def test_haversine_san_francisco_pair_reasonable() -> None:
    # City Hall to Mission St area: roughly 1.2 km apart.
    distance = haversine_distance_m(CENTER_LAT, CENTER_LNG, TRUCK_B.latitude, TRUCK_B.longitude)
    assert 1_100 < distance < 1_400


# ---------------------------------------------------------------------------
# Radius filtering
# ---------------------------------------------------------------------------


def test_radius_filter_excludes_far_trucks() -> None:
    # Default 2 km: TRUCK_A (~0 m) and TRUCK_B (~1.2 km) qualify, TRUCK_C (~2.1 km) does not.
    response = search(ALL_TRUCKS)
    assert [truck.id for truck in response.trucks] == ["1", "2"]
    assert response.total == 2


def test_larger_radius_includes_more_trucks() -> None:
    response = search(ALL_TRUCKS, radius_km=5.0)
    assert [truck.id for truck in response.trucks] == ["1", "2", "3"]
    assert response.total == 3


def test_small_radius_returns_only_center_truck() -> None:
    response = search(ALL_TRUCKS, radius_km=0.1)
    assert [truck.id for truck in response.trucks] == ["1"]


def test_trucks_without_coordinates_are_excluded() -> None:
    response = search(ALL_TRUCKS, radius_km=50.0)
    assert TRUCK_NO_COORDS.id not in [truck.id for truck in response.trucks]


# ---------------------------------------------------------------------------
# Search and filtering
# ---------------------------------------------------------------------------


def test_search_matches_applicant_name() -> None:
    response = search(ALL_TRUCKS, search="golden")
    assert [truck.id for truck in response.trucks] == ["1"]


def test_search_matches_address() -> None:
    response = search(ALL_TRUCKS, search="mission st")
    assert [truck.id for truck in response.trucks] == ["2"]


def test_search_matches_food_items() -> None:
    response = search(ALL_TRUCKS, search="burritos")
    assert [truck.id for truck in response.trucks] == ["2"]


def test_search_is_case_insensitive() -> None:
    response = search(ALL_TRUCKS, search="GOLDEN GRILL")
    assert [truck.id for truck in response.trucks] == ["1"]


def test_search_with_no_match_returns_empty() -> None:
    response = search(ALL_TRUCKS, search="pizza palace")
    assert response.trucks == []
    assert response.total == 0


def test_food_type_filter() -> None:
    response = search(ALL_TRUCKS, food_type="taco")
    assert [truck.id for truck in response.trucks] == ["2"]


def test_food_type_filter_is_case_insensitive() -> None:
    response = search(ALL_TRUCKS, food_type="TACOS")
    assert [truck.id for truck in response.trucks] == ["2"]


def test_food_type_filter_can_be_combined_with_search() -> None:
    # Radius widened: TRUCK_C is ~2.1 km from center, outside the default 2 km.
    response = search(ALL_TRUCKS, radius_km=5.0, food_type="coffee", search="luna")
    assert [truck.id for truck in response.trucks] == ["3"]


# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------


def test_results_are_sorted_nearest_first() -> None:
    response = search(ALL_TRUCKS, radius_km=5.0)
    distances = [truck.distance_m for truck in response.trucks]
    assert distances == sorted(distances)
    assert [truck.id for truck in response.trucks] == ["1", "2", "3"]


def test_response_includes_distance_from_center() -> None:
    response = search(ALL_TRUCKS)
    assert response.trucks[0].distance_m == pytest.approx(0.0, abs=1.0)
    assert response.trucks[1].distance_m == pytest.approx(
        haversine_distance_m(CENTER_LAT, CENTER_LNG, TRUCK_B.latitude, TRUCK_B.longitude),
        abs=1.0,
    )


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


def test_pagination_default_page() -> None:
    response = search(ALL_TRUCKS, radius_km=5.0)
    assert response.limit == 20
    assert response.offset == 0
    assert len(response.trucks) == 3


def test_pagination_limit_and_offset() -> None:
    response = search(ALL_TRUCKS, radius_km=5.0, limit=1, offset=1)
    assert [truck.id for truck in response.trucks] == ["2"]
    assert response.total == 3
    assert response.limit == 1
    assert response.offset == 1


def test_pagination_beyond_results_returns_empty_page() -> None:
    response = search(ALL_TRUCKS, radius_km=5.0, limit=20, offset=100)
    assert response.trucks == []
    assert response.total == 3


def test_pagination_preserves_total_across_pages() -> None:
    page_one = search(ALL_TRUCKS, radius_km=5.0, limit=2, offset=0)
    page_two = search(ALL_TRUCKS, radius_km=5.0, limit=2, offset=2)
    assert page_one.total == 3
    assert page_two.total == 3
    assert len(page_one.trucks) == 2
    assert len(page_two.trucks) == 1


# ---------------------------------------------------------------------------
# Query parameter validation
# ---------------------------------------------------------------------------


def test_query_defaults() -> None:
    params = FoodTruckSearchParams.from_query(lat="37.7793", lng="-122.4193")
    assert params.lat == 37.7793
    assert params.lng == -122.4193
    assert params.radius_km == 2.0
    assert params.limit == 20
    assert params.offset == 0
    assert params.search is None
    assert params.food_type is None


def test_query_parses_custom_values() -> None:
    params = FoodTruckSearchParams.from_query(
        lat="37.7", lng="-122.4", radius="5", food_type="Tacos", search="  Luna ", limit="100", offset="5"
    )
    assert params.radius_km == 5.0
    assert params.food_type == "Tacos"
    assert params.search == "Luna"
    assert params.limit == 100
    assert params.offset == 5


def test_query_requires_both_coordinates() -> None:
    with pytest.raises(InvalidLocationError):
        FoodTruckSearchParams.from_query(lat=None, lng=None)
    with pytest.raises(InvalidLocationError):
        FoodTruckSearchParams.from_query(lat="37.7", lng=None)


@pytest.mark.parametrize(
    "lat,lng",
    [
        ("abc", "-122.4193"),
        ("37.7", "xyz"),
        ("95", "-122.4193"),
        ("-91", "0"),
        ("37.7", "181"),
        ("37.7", "-181"),
    ],
)
def test_query_rejects_invalid_coordinates(lat: str, lng: str) -> None:
    with pytest.raises(InvalidLocationError):
        FoodTruckSearchParams.from_query(lat=lat, lng=lng)


@pytest.mark.parametrize("radius", ["0", "0.05", "50.1", "abc", "-2", "inf"])
def test_query_rejects_invalid_radius(radius: str) -> None:
    with pytest.raises(InvalidRadiusError):
        FoodTruckSearchParams.from_query(lat="37.7", lng="-122.4", radius=radius)


def test_query_accepts_radius_bounds() -> None:
    FoodTruckSearchParams.from_query(lat="37.7", lng="-122.4", radius="0.1")
    FoodTruckSearchParams.from_query(lat="37.7", lng="-122.4", radius="50")


@pytest.mark.parametrize("limit", ["0", "101", "abc", "1.5", "-3"])
def test_query_rejects_invalid_limit(limit: str) -> None:
    with pytest.raises(InvalidPaginationError):
        FoodTruckSearchParams.from_query(lat="37.7", lng="-122.4", limit=limit)


@pytest.mark.parametrize("offset", ["-1", "abc", "2.5"])
def test_query_rejects_invalid_offset(offset: str) -> None:
    with pytest.raises(InvalidPaginationError):
        FoodTruckSearchParams.from_query(lat="37.7", lng="-122.4", offset=offset)


def test_query_treats_blank_filters_as_absent() -> None:
    params = FoodTruckSearchParams.from_query(
        lat="37.7", lng="-122.4", search="   ", food_type=""
    )
    assert params.search is None
    assert params.food_type is None