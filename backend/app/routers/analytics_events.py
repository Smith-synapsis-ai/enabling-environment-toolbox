"""Analytics event ingestion and KPI read endpoints (C3/C4).

Endpoints:
    POST /api/events        — anonymous event ingestion (no auth)
    GET  /api/events/kpi    — aggregate counts by event_name (no auth)
    GET  /api/events/survey — pulse survey analytics (no auth)
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


@router.get("/api/events/survey")
async def get_survey() -> dict:
    """Return pulse-survey analytics from analytics_events.

    Aggregates rows where event_name = 'pulse_survey'. The 1-5 score and the
    optional free-text comment live inside the JSON payload column, parsed here
    with SQLite's json_extract(). Returns totals, average score, a 1-5 score
    distribution, and the 20 most recent responses.

    No authentication required — consistent with GET /api/events/kpi.
    """
    await ensure_db()
    async with get_db() as db:
        # Aggregate: count + average score over all pulse_survey events.
        cursor = await db.execute(
            """
            SELECT
                COUNT(*) AS total,
                AVG(CAST(json_extract(payload, '$.score') AS REAL)) AS avg_score
            FROM analytics_events
            WHERE event_name = ?
            """,
            ("pulse_survey",),
        )
        agg = await cursor.fetchone()

        # Score distribution (1-5) computed in SQL.
        dist_cursor = await db.execute(
            """
            SELECT CAST(json_extract(payload, '$.score') AS INTEGER) AS score,
                   COUNT(*) AS count
            FROM analytics_events
            WHERE event_name = ?
            GROUP BY score
            """,
            ("pulse_survey",),
        )
        dist_rows = await dist_cursor.fetchall()

        # 20 most recent responses.
        recent_cursor = await db.execute(
            """
            SELECT json_extract(payload, '$.score') AS score,
                   json_extract(payload, '$.comment') AS comment,
                   session_id,
                   created_at
            FROM analytics_events
            WHERE event_name = ?
            ORDER BY created_at DESC
            LIMIT 20
            """,
            ("pulse_survey",),
        )
        recent_rows = await recent_cursor.fetchall()

    total_responses = agg["total"] if agg else 0
    avg_raw = agg["avg_score"] if agg else None
    average_score = round(avg_raw, 2) if avg_raw is not None else 0.0

    # Always return all five buckets so the UI can render a stable chart.
    score_distribution: dict[str, int] = {str(i): 0 for i in range(1, 6)}
    for row in dist_rows:
        score = row["score"]
        if score is not None and 1 <= score <= 5:
            score_distribution[str(score)] = row["count"]

    recent = [
        {
            "score": row["score"],
            "comment": row["comment"],
            "session_id": row["session_id"],
            "created_at": row["created_at"],
        }
        for row in recent_rows
    ]

    return {
        "total_responses": total_responses,
        "average_score": average_score,
        "score_distribution": score_distribution,
        "recent": recent,
    }
