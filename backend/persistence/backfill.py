"""One-time backfill of legacy SQLite analytics rows into durable Postgres.

WHY
---
Before C6 Wave A, the C4 KPI access-event count, C3 feature-usage events, and
C5 SQLite survey rows lived in agent_store.db. We are moving the source of
truth to Postgres (decision 5). To avoid losing the current counts on the
cutover, this module copies any rows present in the local SQLite
``analytics_events`` table into the Postgres ``analytics_events`` table, exactly
once, guarded by a marker so it never double-counts on subsequent boots.

Idempotency: a single ``analytics_backfill_done`` row is written to the Postgres
``schema_markers`` table (created here, IF NOT EXISTS). If the marker exists the
backfill is skipped. This is safe across instance refreshes -- the marker lives
in durable Postgres, so a replaced instance sees "already done" and is a no-op,
even though its fresh SQLite file is empty.

This runs at app startup (app.main lifespan). It is fully wrapped log-only:
a backfill failure must NEVER prevent the API from starting.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path

from sqlalchemy import text

from app.database import AsyncSessionLocal

logger = logging.getLogger("ee.backfill")

_MARKER = "analytics_backfill_done"


def _sqlite_path() -> Path:
    return Path(
        os.environ.get("AGENT_STORE_PATH", "/app/backend/data/agent_store.db")
    )


async def _marker_set() -> bool:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_markers (
                    marker TEXT PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        )
        await db.commit()
        result = await db.execute(
            text("SELECT 1 FROM schema_markers WHERE marker = :m"),
            {"m": _MARKER},
        )
        return result.fetchone() is not None


async def _set_marker() -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                "INSERT INTO schema_markers (marker) VALUES (:m) "
                "ON CONFLICT (marker) DO NOTHING"
            ),
            {"m": _MARKER},
        )
        await db.commit()


def _read_sqlite_rows() -> list[tuple]:
    path = _sqlite_path()
    if not path.exists():
        return []
    try:
        conn = sqlite3.connect(str(path))
        try:
            cur = conn.execute(
                "SELECT event_name, session_id, created_at, payload "
                "FROM analytics_events ORDER BY id"
            )
            return cur.fetchall()
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001 — missing table on a fresh DB, etc.
        logger.info("Backfill: no SQLite analytics_events to read (%s)", exc)
        return []


async def backfill_sqlite_to_postgres() -> dict:
    """Copy legacy SQLite analytics_events into Postgres, once. Returns a summary."""
    try:
        if await _marker_set():
            logger.info("Backfill: marker present — already done, skipping.")
            return {"status": "skipped", "reason": "marker_present"}

        rows = _read_sqlite_rows()
        if not rows:
            # Nothing to copy, but still set the marker so we don't re-probe
            # the (now-empty, ephemeral) SQLite file on every future boot.
            await _set_marker()
            logger.info("Backfill: no legacy SQLite rows found — marker set.")
            return {"status": "done", "copied": 0}

        copied = 0
        async with AsyncSessionLocal() as db:
            for event_name, session_id, created_at, payload in rows:
                # payload arrives as a JSON string (or None) from SQLite.
                payload_json = payload if payload else None
                await db.execute(
                    text(
                        """
                        INSERT INTO analytics_events
                            (event_name, session_id, created_at, payload)
                        VALUES
                            (:event_name, :session_id, :created_at,
                             CAST(:payload AS jsonb))
                        """
                    ),
                    {
                        "event_name": event_name,
                        "session_id": session_id,
                        "created_at": created_at,
                        "payload": payload_json,
                    },
                )
                copied += 1
            await db.commit()

        await _set_marker()
        logger.info("Backfill: copied %d legacy SQLite analytics rows to Postgres.", copied)
        return {"status": "done", "copied": copied}
    except Exception as exc:  # noqa: BLE001 — never block startup
        logger.exception("Backfill failed (non-fatal): %s", exc)
        return {"status": "error", "error": str(exc)}
