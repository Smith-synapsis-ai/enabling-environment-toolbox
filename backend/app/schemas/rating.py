"""Pydantic schemas for the tool rating endpoints."""

import uuid

from pydantic import BaseModel, Field


class RatingRequest(BaseModel):
    """Request body for POST /api/tools/{tool_id}/rate."""

    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    user_id: str = Field(..., min_length=1, description="Unique user identifier (e.g. email)")


class RatingResponse(BaseModel):
    """Aggregated rating information for a tool."""

    tool_id: uuid.UUID
    average: float
    count: int
    distribution: dict[str, int] = Field(
        default_factory=lambda: {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
        description="Count of ratings per star level",
    )
