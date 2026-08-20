"""API response schemas."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""

    status: Literal["ok"]
    app: str
    version: str
    environment: str