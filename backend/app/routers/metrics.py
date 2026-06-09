"""Metrics router: aggregate platform statistics.

Endpoint:
    GET /api/metrics  -- returns cached aggregate stats
"""

import logging
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Simple in-memory cache
# ---------------------------------------------------------------------------

_CACHE_TTL_SECONDS = 300  # 5 minutes

_cache: dict = {
    "data": None,
    "expires": 0.0,
}


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class MetricsResponse(BaseModel):
    total_tools: int
    total_frameworks: int
    geography_coverage: int
    total_searches: int
    avg_rating: float


# ---------------------------------------------------------------------------
# GET /api/metrics
# ---------------------------------------------------------------------------


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Return aggregate platform metrics, cached for 5 minutes."""

    now = time.time()

    # Return cached data if still valid
    if _cache["data"] is not None and now < _cache["expires"]:
        return _cache["data"]

    try:
        # Run all the count queries
        total_tools_result = await db.execute(
            text("SELECT COUNT(*) FROM tools WHERE is_visible = true")
        )
        total_tools = total_tools_result.scalar() or 0

        total_frameworks_result = await db.execute(
            text(
                "SELECT COUNT(*) FROM tools WHERE is_visible = true AND type = 'Framework'"
            )
        )
        total_frameworks = total_frameworks_result.scalar() or 0

        geography_result = await db.execute(
            text(
                """
                SELECT COUNT(DISTINCT val)
                FROM tools, unnest(geography) AS val
                WHERE is_visible = true
                """
            )
        )
        geography_coverage = geography_result.scalar() or 0

        searches_result = await db.execute(
            text("SELECT COUNT(*) FROM search_logs")
        )
        total_searches = searches_result.scalar() or 0

        avg_rating_result = await db.execute(
            text(
                """
                SELECT COALESCE(AVG(average_rating), 0)
                FROM tools
                WHERE is_visible = true AND rating_count > 0
                """
            )
        )
        avg_rating = float(avg_rating_result.scalar() or 0)

        response = MetricsResponse(
            total_tools=total_tools,
            total_frameworks=total_frameworks,
            geography_coverage=geography_coverage,
            total_searches=total_searches,
            avg_rating=round(avg_rating, 2),
        )

        # Update cache
        _cache["data"] = response
        _cache["expires"] = now + _CACHE_TTL_SECONDS

        return response

    except Exception:
        logger.exception("Failed to compute metrics")
        # If we have stale cached data, return it rather than failing
        if _cache["data"] is not None:
            return _cache["data"]
        raise
