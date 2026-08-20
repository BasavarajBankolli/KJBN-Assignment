"""Tests for the health check endpoint and application wiring."""

from fastapi.testclient import TestClient

from app.core.config import get_settings


def test_health_returns_ok(client: TestClient) -> None:
    settings = get_settings()
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


def test_health_allows_configured_cors_origin(client: TestClient) -> None:
    settings = get_settings()
    origin = settings.cors_origin_list[0]

    response = client.get("/api/v1/health", headers={"Origin": origin})

    assert response.headers.get("access-control-allow-origin") == origin


def test_docs_page_available(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema_exposes_health_path(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]


def test_unknown_route_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404