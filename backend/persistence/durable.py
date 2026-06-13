"""Durable business-data store backed by Postgres RDS (C6 / Wave A, decision 5).

WHY THIS MODULE EXISTS
----------------------
The anonymous business tables the admin dashboard reads -- ``analytics_events``
(C3 feature usage + C4 KPI access events + C5 pulse-survey rows) and the new
``token_usage`` (C6 token/cost capture) -- previously lived ONLY in the SQLite
``agent_store.db`` on the container's ephemeral root volume. On an ASG instance
refresh that volume is destroyed (``DeleteOnTermination: true``); durability
rested entirely on a best-effort Litestream restore that fails silently. That
is the "KPI/analytics/survey rows lost until a manual ops-fix" failure mode.

Postgres RDS (``ee-toolbox-mgmt-db``) already SURVIVES instance replacement and
the dashboard already reads it, so it is the correct durable home for these
small, append-only, anonymous tables. This module is the single durable
read/write path; it uses the existing async SQLAlchemy engine (raw ``text()``
SQL, same convention as ``app/routers/admin.py`` and ``governance.py``).

The schema is created by Alembic migration ``007_durable_business_tables`` and
is intentionally identical in shape to the old SQLite tables, so the existing
``/api/events/*`` response contracts are preserved byte-for-byte.

All writes are wrapped log-only by the CALLERS (same defensive pattern as the
old ``ingest_event``) -- analytics/telemetry must never break a user turn.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.database import AsyncSessionLocal

logger = logging.getLogger("ee.durable")


def _utc_now() -> str:
    """ISO-8601 UTC, second precision -- matches the legacy created_at convention."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Analytics events (C3 feature usage / C4 KPI access events / C5 survey rows)
# ---------------------------------------------------------------------------

async def record_event(
    event_name: str,
    session_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Insert one anonymous analytics event into durable Postgres storage."""
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                """
                INSERT INTO analytics_events (event_name, session_id, created_at, payload)
                VALUES (:event_name, :session_id, :created_at, CAST(:payload AS jsonb))
                """
            ),
            {
                "event_name": event_name,
                "session_id": session_id,
                "created_at": _utc_now(),
                "payload": json.dumps(payload) if payload else None,
            },
        )
        await db.commit()


async def get_kpi_counts() -> dict[str, int]:
    """Return ``{event_name: count}`` over all durable analytics events."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT event_name, COUNT(*) AS count
                FROM analytics_events
                GROUP BY event_name
                ORDER BY count DESC
                """
            )
        )
        rows = result.mappings().all()
    return {row["event_name"]: int(row["count"]) for row in rows}


async def get_survey() -> dict[str, Any]:
    """Aggregate pulse-survey responses from durable analytics events.

    Mirrors the legacy SQLite ``/api/events/survey`` response shape exactly so
    the existing admin survey card needs no change. Score + comment live in the
    JSONB payload (keys ``score``/``comment``).
    """
    async with AsyncSessionLocal() as db:
        agg_result = await db.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    AVG((payload->>'score')::float) AS avg_score
                FROM analytics_events
                WHERE event_name = 'pulse_survey'
                """
            )
        )
        agg = agg_result.mappings().fetchone()

        dist_result = await db.execute(
            text(
                """
                SELECT (payload->>'score')::int AS score, COUNT(*) AS count
                FROM analytics_events
                WHERE event_name = 'pulse_survey'
                GROUP BY (payload->>'score')::int
                """
            )
        )
        dist_rows = dist_result.mappings().all()

        recent_result = await db.execute(
            text(
                """
                SELECT payload->>'score'   AS score,
                       payload->>'comment' AS comment,
                       session_id,
                       created_at
                FROM analytics_events
                WHERE event_name = 'pulse_survey'
                ORDER BY created_at DESC
                LIMIT 20
                """
            )
        )
        recent_rows = recent_result.mappings().all()

    total_responses = int(agg["total"]) if agg else 0
    avg_raw = agg["avg_score"] if agg else None
    average_score = round(float(avg_raw), 2) if avg_raw is not None else 0.0

    score_distribution: dict[str, int] = {str(i): 0 for i in range(1, 6)}
    for row in dist_rows:
        score = row["score"]
        if score is not None and 1 <= int(score) <= 5:
            score_distribution[str(int(score))] = int(row["count"])

    recent = [
        {
            "score": int(row["score"]) if row["score"] is not None else None,
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


# ---------------------------------------------------------------------------
# Token usage (C6 / Thread 2) -- per (session_id, turn) ResultMessage capture
# ---------------------------------------------------------------------------

async def record_token_usage(
    *,
    session_id: str | None,
    turn: int | None,
    orchestrator_model: str | None,
    subagent_model: str | None,
    num_turns: int | None,
    duration_ms: int | None,
    input_tokens: int | None,
    output_tokens: int | None,
    cache_read_tokens: int | None,
    cache_creation_tokens: int | None,
    total_cost_usd: float | None,
    is_error: bool,
) -> None:
    """Persist one per-turn token-usage row (durable Postgres). Idempotent-ish:
    the orchestrator emits exactly one ResultMessage per turn, so one row per
    (session_id, turn). Callers MUST wrap this log-only (never break a turn).
    """
    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                """
                INSERT INTO token_usage (
                    session_id, turn, created_at,
                    orchestrator_model, subagent_model,
                    num_turns, duration_ms,
                    input_tokens, output_tokens,
                    cache_read_tokens, cache_creation_tokens,
                    total_cost_usd, is_error
                ) VALUES (
                    :session_id, :turn, :created_at,
                    :orchestrator_model, :subagent_model,
                    :num_turns, :duration_ms,
                    :input_tokens, :output_tokens,
                    :cache_read_tokens, :cache_creation_tokens,
                    :total_cost_usd, :is_error
                )
                """
            ),
            {
                "session_id": session_id,
                "turn": turn,
                "created_at": _utc_now(),
                "orchestrator_model": orchestrator_model,
                "subagent_model": subagent_model,
                "num_turns": num_turns,
                "duration_ms": duration_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "total_cost_usd": total_cost_usd,
                "is_error": is_error,
            },
        )
        await db.commit()


async def get_token_summary() -> dict[str, Any]:
    """Totals + averages for the token-usage admin card.

    Benchmark band is the $0.10-0.20/query target from the C6 brief.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT
                    COUNT(*)                          AS runs,
                    COALESCE(SUM(total_cost_usd), 0)  AS total_cost,
                    COALESCE(AVG(total_cost_usd), 0)  AS avg_cost,
                    COALESCE(SUM(input_tokens), 0)    AS total_input,
                    COALESCE(SUM(output_tokens), 0)   AS total_output,
                    COALESCE(SUM(cache_read_tokens), 0)     AS total_cache_read,
                    COALESCE(SUM(cache_creation_tokens), 0) AS total_cache_creation,
                    COALESCE(SUM(num_turns), 0)       AS total_turns
                FROM token_usage
                """
            )
        )
        row = result.mappings().fetchone()

        by_model_result = await db.execute(
            text(
                """
                SELECT COALESCE(orchestrator_model, 'unknown') AS model,
                       COUNT(*) AS runs,
                       COALESCE(SUM(total_cost_usd), 0) AS cost,
                       COALESCE(SUM(input_tokens), 0) AS input_tokens,
                       COALESCE(SUM(output_tokens), 0) AS output_tokens
                FROM token_usage
                GROUP BY orchestrator_model
                ORDER BY cost DESC
                """
            )
        )
        by_model_rows = by_model_result.mappings().all()

    runs = int(row["runs"]) if row else 0
    total_cost = float(row["total_cost"]) if row else 0.0
    avg_cost = float(row["avg_cost"]) if row else 0.0

    return {
        "runs": runs,
        "total_cost_usd": round(total_cost, 4),
        "avg_cost_per_query_usd": round(avg_cost, 4),
        "total_input_tokens": int(row["total_input"]) if row else 0,
        "total_output_tokens": int(row["total_output"]) if row else 0,
        "total_cache_read_tokens": int(row["total_cache_read"]) if row else 0,
        "total_cache_creation_tokens": int(row["total_cache_creation"]) if row else 0,
        "total_turns": int(row["total_turns"]) if row else 0,
        "benchmark_low_usd": 0.10,
        "benchmark_high_usd": 0.20,
        "by_model": [
            {
                "model": r["model"],
                "runs": int(r["runs"]),
                "cost_usd": round(float(r["cost"]), 4),
                "input_tokens": int(r["input_tokens"]),
                "output_tokens": int(r["output_tokens"]),
            }
            for r in by_model_rows
        ],
    }


async def get_token_recent(limit: int = 50) -> list[dict[str, Any]]:
    """Most recent token-usage rows for the admin table."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                """
                SELECT session_id, turn, created_at,
                       orchestrator_model, subagent_model,
                       num_turns, duration_ms,
                       input_tokens, output_tokens,
                       cache_read_tokens, cache_creation_tokens,
                       total_cost_usd, is_error
                FROM token_usage
                ORDER BY created_at DESC, id DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        rows = result.mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Health probe of the durable store (for the honest /health field, decision 4)
# ---------------------------------------------------------------------------

async def durable_health() -> dict[str, Any]:
    """Probe the durable Postgres store; returns connection state + row counts.

    Never raises: returns ``{"connected": False, "error": ...}`` on failure so
    /health can stay HTTP 200 (ALB liveness) while reporting the TRUE state.
    """
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            ev = await db.execute(text("SELECT COUNT(*) FROM analytics_events"))
            tk = await db.execute(text("SELECT COUNT(*) FROM token_usage"))
            return {
                "connected": True,
                "analytics_events": int(ev.scalar() or 0),
                "token_usage": int(tk.scalar() or 0),
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("durable_health probe failed: %s", exc)
        return {"connected": False, "error": str(exc)}
