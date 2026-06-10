"""Session/message store and SQLite report-draft store (Task A7).

``SqliteReportStore`` satisfies the Wave-3 ``ReportStore`` protocol shared
with Task A5 (which ships a ``JsonFileReportStore`` default); the coordinator
swaps the default store at merge time.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from persistence.db import ensure_db, get_db, utc_now_iso


# ---------------------------------------------------------------------------
# ReportStore protocol -- duplicated VERBATIM from the Wave-3 shared interface
# contract (/Users/smithai/workspace/analysis/wave3-interfaces.md §1).
# Do NOT import it from backend/agents/report_state.py: that module is owned
# by Task A5 and does not exist on this branch. The coordinator reconciles
# the two copies at merge time.
# ---------------------------------------------------------------------------

class ReportStore(Protocol):
    async def save_draft(self, session_id: str, draft_json: str) -> None: ...
    async def load_draft(self, session_id: str) -> str | None: ...   # None if absent
    async def list_sessions(self) -> list[str]: ...


class SessionStore:
    """Conversation persistence: sessions and their message/event history.

    ``session_id`` is always the normalized UUID string produced by
    ``orchestrator._normalize_session_id`` (contract §4).
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path

    async def create_session(self, session_id: str, title: str = "") -> dict[str, Any]:
        """Create the session row if absent (idempotent); returns the row."""
        await ensure_db(self._db_path)
        now = utc_now_iso()
        async with get_db(self._db_path) as db:
            await db.execute(
                """INSERT INTO sessions (session_id, created_at, updated_at, title)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at""",
                (session_id, now, now, title),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = await cursor.fetchone()
        return dict(row)

    async def touch_session(self, session_id: str) -> None:
        """Bump ``updated_at`` (used on every appended message)."""
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            await db.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (utc_now_iso(), session_id),
            )
            await db.commit()

    async def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        event_type: str = "",
    ) -> int:
        """Append one message/event; auto-creates the session row; returns row id."""
        await ensure_db(self._db_path)
        now = utc_now_iso()
        async with get_db(self._db_path) as db:
            await db.execute(
                """INSERT INTO sessions (session_id, created_at, updated_at, title)
                   VALUES (?, ?, ?, '')
                   ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at""",
                (session_id, now, now),
            )
            cursor = await db.execute(
                """INSERT INTO messages (session_id, role, content, event_type, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, role, content, event_type, now),
            )
            await db.commit()
            return int(cursor.lastrowid or 0)

    async def get_history(self, session_id: str) -> list[dict[str, Any]]:
        """Full message history for a session, in insertion order."""
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            cursor = await db.execute(
                """SELECT id, session_id, role, content, event_type, created_at
                   FROM messages WHERE session_id = ? ORDER BY id""",
                (session_id,),
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_sessions(self) -> list[dict[str, Any]]:
        """All sessions, most recently updated first."""
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]


class SqliteReportStore:
    """``ReportStore`` implementation over the ``report_drafts`` table.

    ``draft_json`` is an opaque JSON string here -- only A5's report-state
    module defines its schema (contract §1).
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path

    async def save_draft(self, session_id: str, draft_json: str) -> None:
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            await db.execute(
                """INSERT INTO report_drafts (session_id, draft_json, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET
                       draft_json = excluded.draft_json,
                       updated_at = excluded.updated_at""",
                (session_id, draft_json, utc_now_iso()),
            )
            await db.commit()

    async def load_draft(self, session_id: str) -> str | None:
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            cursor = await db.execute(
                "SELECT draft_json FROM report_drafts WHERE session_id = ?",
                (session_id,),
            )
            row = await cursor.fetchone()
        return row["draft_json"] if row else None

    async def list_sessions(self) -> list[str]:
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            cursor = await db.execute(
                "SELECT session_id FROM report_drafts ORDER BY updated_at DESC"
            )
            rows = await cursor.fetchall()
        return [r["session_id"] for r in rows]
