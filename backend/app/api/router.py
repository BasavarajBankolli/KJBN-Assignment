"""Aggregated versioned API router."""

from fastapi import APIRouter

from app.api.routes import food_trucks, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(food_trucks.router)