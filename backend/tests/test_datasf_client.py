"""Tests for the DataSF HTTP client.

DataSF is fully mocked via respx - no live network access.
"""

import httpx
import pytest
import respx

from app.clients.datasf import (
    DATASF_APPROVED_STATUS,
    DATASF_MAX_LIMIT,
    DataSFClient,
    DataSFRawFoodTruck,
    normalize_truck,
)
from app.exceptions.errors import (
    DataSFHttpError,
    DataSFInvalidResponseError,
    DataSFTimeoutError,
    DataSFUnavailableError,
)

DATASF_TEST_URL = "https://datasf.test/resource/rqzj-sfat.json"

RAW_TRUCK = {
    "objectid": "1343831",
    "applicant": "Got Snacks",
    "facilitytype": "Push Cart",
    "cnn": "184001",
    "blocklot": "8714002",
    "address": "1020 03RD ST",
    "permit": "19MFF-00112",
    "status": "APPROVED",
    "fooditems": "sunflower seeds: crackerjacks: bottled water: peanuts: candy",
    "x": "6015168.306",
    "y": "2110364.21",
    "latitude": "37.77551013804947",
    "longitude": "-122.39099930600248",
    "schedule": "http://bsm.sfdpw.org/report.pdf",
    "location": {
        "latitude": "37.77551013804947",
        "longitude": "-122.39099930600248",
        "human_address": '{"address": "", "city": "", "state": "", "zip": ""}',
    },
    ":@computed_region_yftq_j783": "14",
}

RAW_TRUCK_NO_EXTRA = {
    "objectid": 1814452,
    "applicant": "Sanch'ers Taqueria & Catering",
    "facilitytype": "Truck",
    "locationdescription": "BAY SHORE BLVD: SUNNYDALE AVE to COUNTY LINE (2600 - 2698) -- WEST --",
    "address": "2610 BAY SHORE BLVD",
    "permit": "24MFF-00020",
    "status": "APPROVED",
    "fooditems": "Tacos",
    "latitude": "37.708677484233256",
    "longitude": "-122.40551636562863",
}


def make_client() -> DataSFClient:
    return DataSFClient(base_url=DATASF_TEST_URL, timeout_seconds=5.0)


# ---------------------------------------------------------------------------
# normalize_truck / raw schema
# ---------------------------------------------------------------------------


def test_normalize_truck_maps_all_fields() -> None:
    truck = normalize_truck(DataSFRawFoodTruck.model_validate(RAW_TRUCK))

    assert truck.id == "1343831"
    assert truck.applicant == "Got Snacks"
    assert truck.facility_type == "Push Cart"
    assert truck.address == "1020 03RD ST"
    assert truck.permit == "19MFF-00112"
    assert truck.status == "APPROVED"
    assert truck.food_items == "sunflower seeds: crackerjacks: bottled water: peanuts: candy"
    assert truck.latitude == pytest.approx(37.77551013804947)
    assert truck.longitude == pytest.approx(-122.39099930600248)
    assert truck.schedule_url == "http://bsm.sfdpw.org/report.pdf"


def test_normalize_truck_handles_missing_optional_fields() -> None:
    truck = normalize_truck(DataSFRawFoodTruck.model_validate(RAW_TRUCK_NO_EXTRA))

    assert truck.id == "1814452"
    assert truck.location_description is not None
    assert truck.schedule_url is None


def test_normalize_truck_tolerates_missing_coordinates() -> None:
    raw = dict(RAW_TRUCK)
    raw["latitude"] = ""
    raw["longitude"] = None

    truck = normalize_truck(DataSFRawFoodTruck.model_validate(raw))

    assert truck.latitude is None
    assert truck.longitude is None


def test_normalize_truck_falls_back_for_missing_applicant() -> None:
    raw = dict(RAW_TRUCK)
    raw["applicant"] = None

    truck = normalize_truck(DataSFRawFoodTruck.model_validate(raw))

    assert truck.applicant == "Unknown vendor"


# ---------------------------------------------------------------------------
# client behavior
# ---------------------------------------------------------------------------


@respx.mock
async def test_fetch_returns_normalized_trucks() -> None:
    route = respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(200, json=[RAW_TRUCK, RAW_TRUCK_NO_EXTRA])
    )
    client = make_client()

    try:
        trucks = await client.fetch_food_trucks()
    finally:
        await client.aclose()

    assert len(trucks) == 2
    assert trucks[0].id == "1343831"
    assert trucks[1].id == "1814452"

    request = route.calls[0].request
    assert request.url.params["$limit"] == str(DATASF_MAX_LIMIT)
    assert request.url.params["$where"] == f"status='{DATASF_APPROVED_STATUS}'"


@respx.mock
async def test_fetch_ignores_computed_region_fields() -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(200, json=[RAW_TRUCK])
    )
    client = make_client()

    try:
        trucks = await client.fetch_food_trucks()
    finally:
        await client.aclose()

    assert len(trucks) == 1
    assert trucks[0].id == "1343831"


@respx.mock
async def test_fetch_skips_malformed_records_and_keeps_valid_ones() -> None:
    malformed = {"objectid": None, "applicant": "Broken"}
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(200, json=[malformed, RAW_TRUCK])
    )
    client = make_client()

    try:
        trucks = await client.fetch_food_trucks()
    finally:
        await client.aclose()

    assert len(trucks) == 1
    assert trucks[0].id == "1343831"


@respx.mock
async def test_fetch_empty_payload_returns_empty_list() -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(return_value=httpx.Response(200, json=[]))
    client = make_client()

    try:
        trucks = await client.fetch_food_trucks()
    finally:
        await client.aclose()

    assert trucks == []


@respx.mock
async def test_fetch_raises_on_timeout() -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        side_effect=httpx.ReadTimeout("timed out")
    )
    client = make_client()

    with pytest.raises(DataSFTimeoutError):
        try:
            await client.fetch_food_trucks()
        finally:
            await client.aclose()


@respx.mock
async def test_fetch_raises_on_connection_error() -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        side_effect=httpx.ConnectError("connection refused")
    )
    client = make_client()

    with pytest.raises(DataSFUnavailableError):
        try:
            await client.fetch_food_trucks()
        finally:
            await client.aclose()


@respx.mock
async def test_fetch_raises_on_upstream_http_500() -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(500, json={"message": "boom"})
    )
    client = make_client()

    with pytest.raises(DataSFHttpError) as exc_info:
        try:
            await client.fetch_food_trucks()
        finally:
            await client.aclose()

    assert exc_info.value.upstream_status_code == 500
    assert "boom" in exc_info.value.detail


@respx.mock
async def test_fetch_raises_on_upstream_http_404() -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(return_value=httpx.Response(404))
    client = make_client()

    with pytest.raises(DataSFHttpError) as exc_info:
        try:
            await client.fetch_food_trucks()
        finally:
            await client.aclose()

    assert exc_info.value.upstream_status_code == 404


@respx.mock
async def test_fetch_raises_on_invalid_json_body() -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(200, content=b"<html>not json</html>")
    )
    client = make_client()

    with pytest.raises(DataSFInvalidResponseError):
        try:
            await client.fetch_food_trucks()
        finally:
            await client.aclose()


@respx.mock
async def test_fetch_raises_when_body_is_not_a_list() -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(200, json={"error": True, "message": "bad"})
    )
    client = make_client()

    with pytest.raises(DataSFInvalidResponseError):
        try:
            await client.fetch_food_trucks()
        finally:
            await client.aclose()


@respx.mock
async def test_fetch_uses_custom_status_filter() -> None:
    route = respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(200, json=[])
    )
    client = make_client()

    try:
        await client.fetch_food_trucks(status="REQUESTED")
    finally:
        await client.aclose()

    assert route.calls[0].request.url.params["$where"] == "status='REQUESTED'"