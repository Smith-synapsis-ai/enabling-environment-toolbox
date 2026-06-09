"""Non-blocking analytics tracking service.

All methods are designed to be used with FastAPI BackgroundTasks so that
tracking never slows down the request.  Errors are logged and swallowed
-- a failed tracking write must never crash a user-facing endpoint.
"""

import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.middleware.bot_detection import is_bot_user_agent

logger = logging.getLogger(__name__)


class TrackingService:
    """Lightweight service for writing analytics events to the database."""

    # ------------------------------------------------------------------
    # Search logging
    # ------------------------------------------------------------------

    @staticmethod
    async def log_search(
        session_id: Optional[str],
        query: str,
        query_type: str,
        filters: Optional[dict],
        result_count: int,
        result_ids: Optional[list[_uuid.UUID]],
    ) -> None:
        """Log a search event to the search_logs table.

        Runs in its own session so it is independent of the request
        transaction.
        """
        try:
            async with AsyncSessionLocal() as db:
                ids_param = (
                    [str(rid) for rid in result_ids] if result_ids else None
                )
                await db.execute(
                    text(
                        """
                        INSERT INTO search_logs
                            (session_id, query_text, query_type, filters_used,
                             results_count, results_tool_ids)
                        VALUES
                            (:session_id, :query, :query_type, CAST(:filters AS jsonb),
                             :result_count, CAST(:result_ids AS uuid[]))
                        """
                    ),
                    {
                        "session_id": session_id,
                        "query": query,
                        "query_type": query_type,
                        "filters": _json_dumps(filters) if filters else None,
                        "result_count": result_count,
                        "result_ids": ids_param,
                    },
                )
                await db.commit()
        except Exception:
            logger.exception("Failed to log search event")

    # ------------------------------------------------------------------
    # Tool view logging
    # ------------------------------------------------------------------

    @staticmethod
    async def log_tool_view(
        tool_id: _uuid.UUID,
        session_id: Optional[str],
        referrer: Optional[str],
    ) -> None:
        """Log a tool view and increment the tool's view_count."""
        try:
            async with AsyncSessionLocal() as db:
                # Insert into tool_views
                await db.execute(
                    text(
                        """
                        INSERT INTO tool_views (tool_id, session_id, referrer)
                        VALUES (:tool_id, :session_id, :referrer)
                        """
                    ),
                    {
                        "tool_id": str(tool_id),
                        "session_id": session_id,
                        "referrer": referrer,
                    },
                )
                # Increment view_count on the tool
                await db.execute(
                    text(
                        """
                        UPDATE tools
                        SET view_count = view_count + 1
                        WHERE id = :tool_id
                        """
                    ),
                    {"tool_id": str(tool_id)},
                )
                await db.commit()
        except Exception:
            logger.exception("Failed to log tool view for %s", tool_id)

    # ------------------------------------------------------------------
    # Session tracking
    # ------------------------------------------------------------------

    @staticmethod
    async def ensure_session(
        session_id: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Create or update a user session record.

        Detects bots from the user-agent and sets the is_bot flag.
        """
        try:
            bot_flag = is_bot_user_agent(user_agent)

            async with AsyncSessionLocal() as db:
                await db.execute(
                    text(
                        """
                        INSERT INTO user_sessions
                            (session_id, user_agent, ip_address, is_bot)
                        VALUES
                            (:session_id, :user_agent, :ip_address, :is_bot)
                        ON CONFLICT (session_id) DO UPDATE
                        SET last_active_at = now(),
                            user_agent = COALESCE(EXCLUDED.user_agent, user_sessions.user_agent),
                            ip_address = COALESCE(EXCLUDED.ip_address, user_sessions.ip_address),
                            is_bot = COALESCE(EXCLUDED.is_bot, user_sessions.is_bot)
                        """
                    ),
                    {
                        "session_id": session_id,
                        "user_agent": user_agent,
                        "ip_address": ip_address,
                        "is_bot": bot_flag,
                    },
                )
                await db.commit()
        except Exception:
            logger.exception("Failed to ensure session %s", session_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _json_dumps(obj: dict) -> str:
    """Serialize a dict to a JSON string for JSONB parameters."""
    import json
    return json.dumps(obj)
