"""Analytics event ingestion and KPI read endpoints (C3/C4/C5).

Durability (C6 Wave A, decision 5): these endpoints now read/write the DURABLE
Postgres store (persistence.durable) instead of the ephemeral SQLite
agent_store.db. The response contracts are unchanged. See persistence/durable.py
and alembic 007_durable_business_tables for why.

Endpoints:
    POST /api/events        — anonymous event ingestion (no auth)
    GET  /api/events/kpi    — aggregate counts by event_name (no auth)
    GET  /api/events/survey — pulse survey analytics (no auth)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from persistence.durable import get_kpi_counts, get_survey, record_event

logger = logging.getLogger("ee.analytics")

router = APIRouter()


class IngestRequest(BaseModel):
    event_name: str
    session_id: str | None = None
    payload: dict[str, Any] | None = None


@router.post("/api/events")
async def ingest_event(body: IngestRequest) -> dict:
    """Record an anonymous analytics event in the durable Postgres store.

    Returns {"ok": true} always — errors are logged but not surfaced to the
    client so analytics never break the UI (same defensive contract as before).
    """
    try:
        await record_event(body.event_name, body.session_id, body.payload)
    except Exception:
        logger.exception("Failed to record analytics event %s", body.event_name)
    return {"ok": True}


@router.get("/api/events/kpi")
async def get_kpi() -> dict:
    """Return aggregate event counts grouped by event_name (durable Postgres).

    Also returns the total 'access_event' count as the KPI progress toward the
    5,000 platform-access target. The frontend already de-duplicates access
    events per browser session (App.tsx 'ee-access-tracked' guard), so this
    count is the de-duplicated access-event KPI for G4 (decision 2).

    No authentication required — counts are anonymous aggregates.
    """
    counts = await get_kpi_counts()
    access_total = counts.get("access_event", 0)
    return {
        "kpi_access_events": access_total,
        "kpi_target": 5000,
        "kpi_progress_pct": round(access_total / 5000 * 100, 2),
        "counts_by_event": counts,
    }


@router.get("/api/events/survey")
async def get_survey_endpoint() -> dict:
    """Return pulse-survey analytics from the durable Postgres store.

    Canonical C5 source for the dashboard (decision 1): aggregates rows where
    event_name = 'pulse_survey'. The legacy Postgres pulse_survey_responses
    table is deprecated for display and intentionally not surfaced here.

    No authentication required — consistent with GET /api/events/kpi.
    """
    return await get_survey()
