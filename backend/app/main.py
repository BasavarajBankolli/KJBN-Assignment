"""FastAPI application entry point for the Food Truck Finder backend.

The backend acts as a service layer between web clients and the public
DataSF Food Trucks API. It exposes a versioned JSON REST API at ``/api/v1``
and proxies external data through an internal HTTP client so that clients
never talk to DataSF directly.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging

API_V1_PREFIX = "/api/v1"

settings = get_settings()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Food Truck Finder API - discovers food trucks near a geographic "
            "location using the public DataSF Food Trucks dataset as the data source."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=API_V1_PREFIX)

    return app


app = create_app()