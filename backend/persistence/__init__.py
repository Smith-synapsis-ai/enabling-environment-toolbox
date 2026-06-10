"""Agent-side persistence package (Task A7).

SQLite (aiosqlite) store for sessions, messages, report drafts, memories,
and seeded reference knowledge. This is a SEPARATE database from the FastAPI
app DB (``backend/app``) by design -- see
``/Users/smithai/workspace/analysis/a7-persistence-decision.md``.

Public surface:
  - db:      connection management + idempotent ``init_db()`` (WAL mode)
  - store:   ``SessionStore`` (sessions/messages) and ``SqliteReportStore``
             (implements the Wave-3 ``ReportStore`` protocol)
  - memory:  ``MemoryStore`` (store/recall/list/forget, FTS5 + bm25)
"""

from persistence.db import DB_PATH, ensure_db, get_db, init_db
from persistence.memory import VALID_CATEGORIES, MemoryStore
from persistence.store import ReportStore, SessionStore, SqliteReportStore

__all__ = [
    "DB_PATH",
    "ensure_db",
    "get_db",
    "init_db",
    "MemoryStore",
    "VALID_CATEGORIES",
    "ReportStore",
    "SessionStore",
    "SqliteReportStore",
]
