"""Analytics event ingestion and KPI read endpoints (C3/C4).

Endpoints:
    POST /api/events     — anonymous event ingestion (no auth)
    GET  /api/events/kpi — aggregate counts by event_name (no auth)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from persistence.db import ensure_db, get_db

logger = logging.getLogger("ee.analytics")

router = APIRouter()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class EventPayload:
    """Simple data class — FastAPI BaseModel alternative to avoid pydantic import."""
    pass


from pydantic import BaseModel
from typing import Any


class IngestRequest(BaseModel):
    event_name: str
    session_id: str | None = None
    payload: dict[str, Any] | None = None


@router.post("/api/events")
async def ingest_event(body: IngestRequest) -> dict:
    """Record an anonymous analytics event.

    Accepts any event_name string. session_id is optional. payload is stored
    as JSON. Returns {"ok": true} always — errors are logged but not surfaced
    to the client so analytics never break the UI.
    """
    try:
        await ensure_db()
        async with get_db() as db:
            await db.execute(
                """
                INSERT INTO analytics_events (event_name, session_id, created_at, payload)
                VALUES (?, ?, ?, ?)
                """,
                (
                    body.event_name,
                    body.session_id,
                    _utc_now(),
                    json.dumps(body.payload) if body.payload else None,
                ),
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to record analytics event %s", body.event_name)
    return {"ok": True}


@router.get("/api/events/kpi")
async def get_kpi() -> dict:
    """Return aggregate event counts grouped by event_name.

    Also returns the total 'access_event' count as the KPI progress
    toward the 5,000 platform access target.

    No authentication required — counts are anonymous aggregates.
    """
    await ensure_db()
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT event_name, COUNT(*) AS count
            FROM analytics_events
            GROUP BY event_name
            ORDER BY count DESC
            """
        )
        rows = await cursor.fetchall()

    counts: dict[str, int] = {row["event_name"]: row["count"] for row in rows}
    access_total = counts.get("access_event", 0)

    return {
        "kpi_access_events": access_total,
        "kpi_target": 5000,
        "kpi_progress_pct": round(access_total / 5000 * 100, 2),
        "counts_by_event": counts,
    }
