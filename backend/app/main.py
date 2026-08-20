"""FastAPI application entry point for the Food Truck Finder backend.

The backend acts as a service layer between web clients and the public
DataSF Food Trucks API. It exposes a versioned JSON REST API at ``/api/v1``
and proxies external data through an internal HTTP client so that clients
never talk to DataSF directly.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.clients.datasf import create_datasf_client
from app.core.cache import TTLCache
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.exceptions.errors import AppError
from app.schemas.food_truck import FoodTruck
from app.services.food_trucks import FoodTruckService

API_V1_PREFIX = "/api/v1"

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create application-scoped resources and clean them up on shutdown."""
    datasf_client = create_datasf_client(
        base_url=settings.datasf_base_url,
        timeout_seconds=settings.datasf_timeout_seconds,
    )
    cache = TTLCache[list[FoodTruck]](ttl_seconds=settings.cache_ttl_seconds)
    app.state.food_truck_service = FoodTruckService(client=datasf_client, cache=cache)
    logger.info(
        "Food Truck Finder API started (env=%s, datasf=%s, cache_ttl=%ss)",
        settings.app_env,
        settings.datasf_base_url,
        settings.cache_ttl_seconds,
    )
    try:
        yield
    finally:
        await datasf_client.aclose()
        logger.info("Food Truck Finder API shut down")


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
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=API_V1_PREFIX)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """Render application errors in the consistent error envelope."""
        if exc.status_code >= 500:
            logger.error("API error %s on %s %s: %s", exc.code, request.method, request.url.path, exc.detail)
        else:
            logger.warning("API error %s on %s %s: %s", exc.code, request.method, request.url.path, exc.detail)
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Last-resort handler: log details, never leak internals to clients."""
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=AppError().to_dict(),
        )

    return app


app = create_app()