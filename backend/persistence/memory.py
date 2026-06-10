"""MemoryStore: store/recall/list/forget over the ``memories`` table (Task A7).

Recall is FTS5 MATCH with bm25 ranking (OR-joined quoted tokens), falling back
to LIKE when the query yields no FTS-safe tokens. When no category filter is
given, recall also surfaces matches from the ``seed_knowledge`` table (the
eight-pillar taxonomy + tool-metadata schema seeded by scripts/seed_memory.py);
seed entries sit OUTSIDE the fixed category list on purpose -- see
/Users/smithai/workspace/analysis/a7-persistence-decision.md.

``category`` is validated against the FIXED Wave-3 list
(/Users/smithai/workspace/analysis/wave3-interfaces.md §3). Invalid categories
return an error dict -- never silent acceptance.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from persistence.db import ensure_db, get_db, utc_now_iso

# FIXED list -- wave3-interfaces.md §3. Frozen for Wave 3; do not extend.
VALID_CATEGORIES: tuple[str, ...] = (
    "challenge_context",
    "tool_recommendations",
    "accepted_pathways",
    "report_drafts",
    "session_history",
    "user_preferences",
    "feedback_signals",
)


def _fts_query(query: str) -> str | None:
    """Build an FTS5 MATCH expression from free text.

    Each alphanumeric token is double-quoted (so FTS5 operators/punctuation in
    user text cannot break the query) and tokens are OR-joined for recall-style
    matching. Returns None when the text has no FTS-safe tokens (caller falls
    back to LIKE).
    """
    tokens = re.findall(r"[A-Za-z0-9_]+", query)
    if not tokens:
        return None
    return " OR ".join(f'"{t}"' for t in tokens)


class MemoryStore:
    """Persistent memory with FTS5 search, backed by the agent store DB."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path

    async def store(
        self,
        category: str,
        content: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Store one memory. Invalid category -> error dict (never silent)."""
        if category not in VALID_CATEGORIES:
            return {
                "error": (
                    f"Invalid category {category!r}. "
                    f"Valid categories: {', '.join(VALID_CATEGORIES)}"
                )
            }
        content = (content or "").strip()
        if not content:
            return {"error": "Memory content must be a non-empty string."}
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            cursor = await db.execute(
                """INSERT INTO memories (category, content, session_id, created_at)
                   VALUES (?, ?, ?, ?)""",
                (category, content, session_id, utc_now_iso()),
            )
            await db.commit()
            memory_id = int(cursor.lastrowid or 0)
        return {
            "id": memory_id,
            "category": category,
            "content": content,
            "session_id": session_id,
            "stored": True,
        }

    async def recall(
        self,
        query: str,
        category: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Ranked search across memories (and seed knowledge when unfiltered)."""
        if category is not None and category not in VALID_CATEGORIES:
            return {
                "error": (
                    f"Invalid category {category!r}. "
                    f"Valid categories: {', '.join(VALID_CATEGORIES)}"
                )
            }
        limit = max(1, min(int(limit), 50))
        match_expr = _fts_query(query or "")
        await ensure_db(self._db_path)
        results: list[dict[str, Any]] = []
        async with get_db(self._db_path) as db:
            # --- memories ---
            if match_expr is not None:
                sql = (
                    "SELECT m.id, m.category, m.content, m.session_id, "
                    "       m.created_at, bm25(memories_fts) AS rank "
                    "FROM memories_fts JOIN memories m ON m.id = memories_fts.rowid "
                    "WHERE memories_fts MATCH ?"
                )
                params: list[Any] = [match_expr]
                if category:
                    sql += " AND m.category = ?"
                    params.append(category)
                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)
                cursor = await db.execute(sql, params)
            else:
                sql = (
                    "SELECT id, category, content, session_id, created_at, "
                    "       0.0 AS rank FROM memories WHERE content LIKE ?"
                )
                params = [f"%{(query or '').strip()}%"]
                if category:
                    sql += " AND category = ?"
                    params.append(category)
                sql += " ORDER BY id DESC LIMIT ?"
                params.append(limit)
                cursor = await db.execute(sql, params)
            for r in await cursor.fetchall():
                results.append(
                    {
                        "source": "memory",
                        "id": r["id"],
                        "category": r["category"],
                        "content": r["content"],
                        "session_id": r["session_id"],
                        "created_at": r["created_at"],
                        "rank": r["rank"],
                    }
                )

            # --- seed knowledge (reference data; only when no category filter,
            #     because seed entries have a `kind`, not a category) ---
            if category is None:
                if match_expr is not None:
                    cursor = await db.execute(
                        "SELECT s.id, s.key, s.kind, s.content, "
                        "       bm25(seed_knowledge_fts) AS rank "
                        "FROM seed_knowledge_fts "
                        "JOIN seed_knowledge s ON s.id = seed_knowledge_fts.rowid "
                        "WHERE seed_knowledge_fts MATCH ? "
                        "ORDER BY rank LIMIT ?",
                        (match_expr, limit),
                    )
                else:
                    cursor = await db.execute(
                        "SELECT id, key, kind, content, 0.0 AS rank "
                        "FROM seed_knowledge WHERE content LIKE ? "
                        "ORDER BY id LIMIT ?",
                        (f"%{(query or '').strip()}%", limit),
                    )
                for r in await cursor.fetchall():
                    results.append(
                        {
                            "source": "seed_knowledge",
                            "id": r["id"],
                            "key": r["key"],
                            "kind": r["kind"],
                            "content": r["content"],
                            "rank": r["rank"],
                        }
                    )

        # bm25 rank: lower is better; LIKE fallbacks carry rank 0.0 and keep
        # their per-source ordering. Stable sort keeps that intuition intact.
        results.sort(key=lambda item: item["rank"])
        return {"query": query, "category": category, "results": results[:limit]}

    async def list(
        self,
        category: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Compact listing of memories, newest first."""
        if category is not None and category not in VALID_CATEGORIES:
            return {
                "error": (
                    f"Invalid category {category!r}. "
                    f"Valid categories: {', '.join(VALID_CATEGORIES)}"
                )
            }
        limit = max(1, min(int(limit), 200))
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            if category:
                cursor = await db.execute(
                    "SELECT id, category, content, session_id, created_at "
                    "FROM memories WHERE category = ? ORDER BY id DESC LIMIT ?",
                    (category, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT id, category, content, session_id, created_at "
                    "FROM memories ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
            rows = [dict(r) for r in await cursor.fetchall()]
        return {"category": category, "count": len(rows), "memories": rows}

    async def forget(self, memory_id: int) -> dict[str, Any]:
        """Hard-delete one memory; returns what was deleted (or an error)."""
        await ensure_db(self._db_path)
        async with get_db(self._db_path) as db:
            cursor = await db.execute(
                "SELECT id, category, content, session_id, created_at "
                "FROM memories WHERE id = ?",
                (memory_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return {"error": f"No memory with id {memory_id}."}
            deleted = dict(row)
            await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            await db.commit()
        return {"deleted": deleted}
