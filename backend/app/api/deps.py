"""Shared FastAPI dependencies."""

from fastapi import Request

from app.services.food_trucks import FoodTruckService


def get_food_truck_service(request: Request) -> FoodTruckService:
    """Resolve the application-scoped food truck service instance."""
    return request.app.state.food_truck_service