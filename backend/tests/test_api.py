"""Integration tests for the food trucks API.

DataSF is fully mocked via respx - the app's HTTP client is intercepted
at the transport level, so no live network access occurs.
"""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from tests.mock_data import (
    ALL_TRUCKS,
    CENTER_LAT,
    CENTER_LNG,
    DATASF_TEST_URL,
    TRUCK_A,
    TRUCK_B,
    TRUCK_C,
    raw_record,
)

RAW_PAYLOAD = [raw_record(truck) for truck in ALL_TRUCKS]

SF_QUERY = {"lat": str(CENTER_LAT), "lng": str(CENTER_LNG)}


def expect_datasf(payload: list | None = None, status: int = 200) -> None:
    kwargs = {"json": payload} if payload is not None else {}
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(status, **kwargs)
    )


# ---------------------------------------------------------------------------
# Success paths
# ---------------------------------------------------------------------------


@respx.mock
def test_food_trucks_returns_results_sorted_nearest_first(client: TestClient) -> None:
    expect_datasf(RAW_PAYLOAD)

    response = client.get("/api/v1/food-trucks", params=SF_QUERY)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [truck["id"] for truck in body["trucks"]] == ["1", "2"]
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["radius_km"] == 2.0
    assert body["center"] == {"latitude": CENTER_LAT, "longitude": CENTER_LNG}
    assert body["trucks"][0]["distance_m"] < 10
    assert body["trucks"][1]["distance_m"] > 1_000


@respx.mock
def test_food_trucks_returns_expected_response_shape(client: TestClient) -> None:
    expect_datasf(RAW_PAYLOAD)

    response = client.get("/api/v1/food-trucks", params=SF_QUERY)

    assert set(response.json().keys()) == {
        "trucks",
        "total",
        "limit",
        "offset",
        "center",
        "radius_km",
    }
    truck = response.json()["trucks"][0]
    assert set(truck.keys()) == {
        "id",
        "applicant",
        "facility_type",
        "location_description",
        "address",
        "food_items",
        "latitude",
        "longitude",
        "distance_m",
    }
    # Internal DataSF details must never leak into the response.
    assert "schedule_url" not in truck
    assert "permit" not in truck
    assert "status" not in truck


@respx.mock
def test_food_trucks_respects_radius_parameter(client: TestClient) -> None:
    expect_datasf(RAW_PAYLOAD)

    response = client.get(
        "/api/v1/food-trucks", params={**SF_QUERY, "radius": "5"}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3


@respx.mock
def test_food_trucks_filters_by_food_type(client: TestClient) -> None:
    expect_datasf(RAW_PAYLOAD)

    response = client.get(
        "/api/v1/food-trucks", params={**SF_QUERY, "food_type": "taco"}
    )

    assert response.status_code == 200
    assert [truck["id"] for truck in response.json()["trucks"]] == ["2"]


@respx.mock
def test_food_trucks_searches_by_text(client: TestClient) -> None:
    expect_datasf(RAW_PAYLOAD)

    response = client.get(
        "/api/v1/food-trucks", params={**SF_QUERY, "search": "golden"}
    )

    assert response.status_code == 200
    assert [truck["id"] for truck in response.json()["trucks"]] == ["1"]


@respx.mock
def test_food_trucks_paginates(client: TestClient) -> None:
    expect_datasf(RAW_PAYLOAD)

    response = client.get(
        "/api/v1/food-trucks", params={**SF_QUERY, "radius": "5", "limit": "1", "offset": "1"}
    )

    assert response.status_code == 200
    body = response.json()
    assert [truck["id"] for truck in body["trucks"]] == ["2"]
    assert body["total"] == 3


@respx.mock
def test_food_trucks_no_results_returns_empty_page(client: TestClient) -> None:
    expect_datasf(RAW_PAYLOAD)

    response = client.get(
        "/api/v1/food-trucks", params={**SF_QUERY, "search": "pizza palace"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["trucks"] == []
    assert body["total"] == 0


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"lat": str(CENTER_LAT)},
        {"lng": str(CENTER_LNG)},
        {"lat": "abc", "lng": str(CENTER_LNG)},
        {"lat": "95", "lng": str(CENTER_LNG)},
        {"lat": str(CENTER_LAT), "lng": "181"},
    ],
)
def test_invalid_location_returns_error_envelope(params: dict, client: TestClient) -> None:
    response = client.get("/api/v1/food-trucks", params=params)

    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "INVALID_LOCATION", "message": response.json()["error"]["message"]}
    }


@pytest.mark.parametrize("radius", ["0", "0.05", "50.1", "abc"])
def test_invalid_radius_returns_error_envelope(radius: str, client: TestClient) -> None:
    response = client.get(
        "/api/v1/food-trucks", params={**SF_QUERY, "radius": radius}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_RADIUS"


@pytest.mark.parametrize("limit", ["0", "101", "abc"])
def test_invalid_limit_returns_error_envelope(limit: str, client: TestClient) -> None:
    response = client.get(
        "/api/v1/food-trucks", params={**SF_QUERY, "limit": limit}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PAGINATION"


@pytest.mark.parametrize("offset", ["-1", "abc"])
def test_invalid_offset_returns_error_envelope(offset: str, client: TestClient) -> None:
    response = client.get(
        "/api/v1/food-trucks", params={**SF_QUERY, "offset": offset}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PAGINATION"


def test_error_envelope_shape_is_consistent(client: TestClient) -> None:
    response = client.get("/api/v1/food-trucks", params={"lat": "99", "lng": "0"})

    assert set(response.json().keys()) == {"error"}
    assert set(response.json()["error"].keys()) == {"code", "message"}


# ---------------------------------------------------------------------------
# DataSF failure handling
# ---------------------------------------------------------------------------


@respx.mock
def test_datasf_http_failure_returns_502_envelope(client: TestClient) -> None:
    expect_datasf(payload=None, status=500)

    response = client.get("/api/v1/food-trucks", params=SF_QUERY)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DATASF_UNAVAILABLE"
    assert "Traceback" not in response.text
    assert "exc" not in response.text.lower()


@respx.mock
def test_datasf_timeout_returns_504_envelope(client: TestClient) -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        side_effect=httpx.ReadTimeout("timed out")
    )

    response = client.get("/api/v1/food-trucks", params=SF_QUERY)

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "DATASF_TIMEOUT"


@respx.mock
def test_datasf_invalid_json_returns_502_envelope(client: TestClient) -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(200, content=b"<html>not json</html>")
    )

    response = client.get("/api/v1/food-trucks", params=SF_QUERY)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DATASF_INVALID_RESPONSE"


@respx.mock
def test_datasf_non_list_body_returns_502_envelope(client: TestClient) -> None:
    respx.get(url__startswith=DATASF_TEST_URL).mock(
        return_value=httpx.Response(200, json={"error": True})
    )

    response = client.get("/api/v1/food-trucks", params=SF_QUERY)

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "DATASF_INVALID_RESPONSE"