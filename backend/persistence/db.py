"""aiosqlite connection management + schema for the agent store (Task A7).

Single SQLite file at ``backend/data/agent_store.db`` in WAL journal mode --
deliberately Litestream-compatible (Litestream replication itself is Phase B,
task B2; nothing here depends on it).

Connections are short-lived (one per operation, the synapsis reference
pattern): with WAL mode this is safe across concurrent processes and keeps
the module free of event-loop-bound singletons.

``init_db()`` is idempotent (CREATE ... IF NOT EXISTS throughout) and may be
called on every startup. ``ensure_db()`` is a cheap per-process guard that
runs ``init_db()`` at most once per database path.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

# backend/persistence/db.py -> parents[1] == backend/
DATA_DIR: Path = Path(__file__).resolve().parents[1] / "data"
DB_PATH: Path = DATA_DIR / "agent_store.db"

# WAL first: Litestream requires WAL-mode databases. synchronous=NORMAL is
# the recommended pairing (durable at the WAL level, much faster commits).
_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA foreign_keys=ON",
)


def utc_now_iso() -> str:
    """Timestamp convention for every *_at TEXT column in this store."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@asynccontextmanager
async def get_db(db_path: str | Path | None = None):
    """Async context manager yielding a configured aiosqlite connection.

    Row factory is ``aiosqlite.Row`` so columns are addressable by name.
    The connection is always closed on exit, including on exceptions.
    """
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(path)
    try:
        db.row_factory = aiosqlite.Row
        for pragma in _PRAGMAS:
            await db.execute(pragma)
        yield db
    finally:
        await db.close()


async def init_db(db_path: str | Path | None = None) -> None:
    """Create all tables, indexes, FTS5 mirrors and sync triggers (idempotent)."""
    async with get_db(db_path) as db:
        # -- Sessions (contract schema, wave3-interfaces.md / task A7) --
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TEXT,
                updated_at TEXT,
                title TEXT
            )
        """)

        # -- Messages --
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                event_type TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages (session_id, id)
        """)

        # -- Report drafts (EXACT contract schema, wave3-interfaces.md §1) --
        await db.execute("""
            CREATE TABLE IF NOT EXISTS report_drafts (
                session_id TEXT PRIMARY KEY,
                draft_json TEXT,
                updated_at TEXT
            )
        """)

        # -- Memories --
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                content TEXT,
                session_id TEXT,
                created_at TEXT
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_category
            ON memories (category)
        """)

        # FTS5 external-content mirror of memories(content, category), kept
        # in sync via AFTER INSERT/DELETE/UPDATE triggers (standard FTS5
        # external-content pattern; the synapsis reference syncs manually,
        # triggers are sturdier -- no code path can forget the index).
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content, category,
                content='memories',
                content_rowid='id'
            )
        """)
        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_fts_ai
            AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts (rowid, content, category)
                VALUES (new.id, new.content, new.category);
            END
        """)
        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_fts_ad
            AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts (memories_fts, rowid, content, category)
                VALUES ('delete', old.id, old.content, old.category);
            END
        """)
        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_fts_au
            AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts (memories_fts, rowid, content, category)
                VALUES ('delete', old.id, old.content, old.category);
                INSERT INTO memories_fts (rowid, content, category)
                VALUES (new.id, new.content, new.category);
            END
        """)

        # -- Seed knowledge (reference data OUTSIDE the fixed memory-category
        #    list; surfaced through MemoryStore.recall). ``key`` is the
        #    idempotency handle for scripts/seed_memory.py. --
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seed_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                kind TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        await db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS seed_knowledge_fts USING fts5(
                content, kind,
                content='seed_knowledge',
                content_rowid='id'
            )
        """)
        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS seed_fts_ai
            AFTER INSERT ON seed_knowledge BEGIN
                INSERT INTO seed_knowledge_fts (rowid, content, kind)
                VALUES (new.id, new.content, new.kind);
            END
        """)
        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS seed_fts_ad
            AFTER DELETE ON seed_knowledge BEGIN
                INSERT INTO seed_knowledge_fts (seed_knowledge_fts, rowid, content, kind)
                VALUES ('delete', old.id, old.content, old.kind);
            END
        """)
        await db.execute("""
            CREATE TRIGGER IF NOT EXISTS seed_fts_au
            AFTER UPDATE ON seed_knowledge BEGIN
                INSERT INTO seed_knowledge_fts (seed_knowledge_fts, rowid, content, kind)
                VALUES ('delete', old.id, old.content, old.kind);
                INSERT INTO seed_knowledge_fts (rowid, content, kind)
                VALUES (new.id, new.content, new.kind);
            END
        """)

        await db.commit()


_initialized: set[str] = set()


async def ensure_db(db_path: str | Path | None = None) -> None:
    """Run ``init_db()`` once per database path per process (cheap guard)."""
    key = str(Path(db_path) if db_path else DB_PATH)
    if key in _initialized:
        return
    await init_db(db_path)
    _initialized.add(key)
