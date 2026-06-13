"""Admin-gated system endpoints (C6 Wave A): token usage + system health.

All endpoints reuse the shared ``verify_admin_token`` dependency (same auth as
every other admin router) and read the DURABLE Postgres store
(persistence.durable). Read-only; purely additive.

Endpoints:
    GET /api/admin/token-usage/summary  — totals, avg $/query vs benchmark, by-model
    GET /api/admin/token-usage/recent   — most recent per-turn token rows
    GET /api/admin/system/health        — honest /health + durable-store state
"""

from __future__ import annotations

import logging
import os
import sqlite3

from fastapi import APIRouter, Depends, Query

from app.routers.admin import verify_admin_token
from persistence.durable import durable_health, get_token_recent, get_token_summary

logger = logging.getLogger("ee.admin_system")

router = APIRouter()


@router.get("/admin/token-usage/summary")
async def token_usage_summary(_user: str = Depends(verify_admin_token)) -> dict:
    """Token-usage totals + averages for the admin dashboard card."""
    return await get_token_summary()


@router.get("/admin/token-usage/recent")
async def token_usage_recent(
    limit: int = Query(50, ge=1, le=500),
    _user: str = Depends(verify_admin_token),
) -> dict:
    """Most recent per-turn token-usage rows for the admin table."""
    rows = await get_token_recent(limit=limit)
    return {"rows": rows, "limit": limit}


@router.get("/admin/system/health")
async def system_health(_user: str = Depends(verify_admin_token)) -> dict:
    """Honest system-health snapshot for the admin dashboard (decision 4).

    Reports BOTH the ephemeral SQLite session store's true state AND the durable
    Postgres business-data store's state + row counts. This is the same data
    /health exposes, but admin-gated and enriched with durable row counts.
    """
    # SQLite session store (ephemeral; Litestream-restored)
    sqlite_path = os.environ.get("AGENT_STORE_PATH", "/app/backend/data/agent_store.db")
    sqlite_state: str
    try:
        if os.path.exists(sqlite_path):
            with sqlite3.connect(sqlite_path, check_same_thread=False) as conn:
                conn.execute("SELECT 1")
            sqlite_state = "connected"
        else:
            sqlite_state = "initializing"
    except Exception as exc:  # noqa: BLE001
        sqlite_state = f"error: {exc}"

    # Detectable signal from the non-silent restore-on-boot check (entrypoint.sh)
    restore_failed_marker = os.path.join(os.path.dirname(sqlite_path), ".restore_failed")
    restore_failed = os.path.exists(restore_failed_marker)
    restore_failed_detail = None
    if restore_failed:
        try:
            with open(restore_failed_marker) as fh:
                restore_failed_detail = fh.read().strip()
        except Exception:  # noqa: BLE001
            restore_failed_detail = "marker present (unreadable)"

    # Detectable signal from the supervised Litestream replicate daemon
    # (entrypoint.sh Step 0 fix): present iff the daemon failed to stay up or
    # exited. Its ABSENCE on a running instance means replication is live.
    replicate_failed_marker = os.path.join(os.path.dirname(sqlite_path), ".replicate_failed")
    replicate_failed = os.path.exists(replicate_failed_marker)
    replicate_failed_detail = None
    if replicate_failed:
        try:
            with open(replicate_failed_marker) as fh:
                replicate_failed_detail = fh.read().strip()
        except Exception:  # noqa: BLE001
            replicate_failed_detail = "marker present (unreadable)"

    durable = await durable_health()

    overall_ok = (
        durable.get("connected", False)
        and sqlite_state in ("connected", "initializing")
        and not restore_failed
        and not replicate_failed
    )

    return {
        "status": "ok" if overall_ok else "degraded",
        "session_store_sqlite": {
            "state": sqlite_state,
            "path": sqlite_path,
            "restore_failed": restore_failed,
            "restore_failed_detail": restore_failed_detail,
            "replication_failed": replicate_failed,
            "replication_failed_detail": replicate_failed_detail,
        },
        "durable_store_postgres": durable,
    }
