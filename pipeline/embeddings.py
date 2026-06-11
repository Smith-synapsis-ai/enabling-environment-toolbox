"""Vector embedding generation for the Enabling Environment Toolbox.

Uses OpenAI's text-embedding-3-small model (1536 dimensions) to generate
embeddings from tool text fields.  These embeddings are stored in the
pgvector ``embedding`` column of the ``tools`` table and used for
semantic similarity search.

All functions are synchronous, consistent with the rest of the pipeline
package.
"""

import logging
import time
from typing import Optional

import openai
import psycopg2

from pipeline.config import DATABASE_URL_SYNC

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# Lazy-initialised client — defers OPENAI_API_KEY lookup to first call so
# test code that never calls embedding functions can import this module safely.
_client: openai.OpenAI | None = None


def _get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        _client = openai.OpenAI()
    return _client


# ---------------------------------------------------------------------------
# Core embedding function
# ---------------------------------------------------------------------------


def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dim embedding vector for the given text.

    Args:
        text: The text to embed.  Should be a concatenation of the tool's
              descriptive fields (title, summary, what_it_does, etc.).

    Returns:
        A list of 1536 floats.

    Raises:
        openai.OpenAIError: On API failure.
        ValueError: If *text* is empty after stripping.
    """
    clean = text.strip()
    if not clean:
        raise ValueError("Cannot embed empty text")

    response = _get_client().embeddings.create(
        input=clean,
        model=EMBEDDING_MODEL,
    )
    vector = response.data[0].embedding

    if len(vector) != EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"Expected {EMBEDDING_DIMENSION}-dim vector, got {len(vector)}"
        )

    return vector


def build_embedding_text(
    title: str = "",
    summary: str = "",
    what_it_does: str = "",
    when_to_use_it: str = "",
    who_its_for: str = "",
) -> str:
    """Concatenate tool text fields into a single string for embedding.

    The order is deliberate: title carries the most semantic weight, followed
    by the structured description fields.  Fields are separated by newlines
    so the embedding model sees distinct sentences.
    """
    parts = [
        p.strip()
        for p in [title, summary, what_it_does, when_to_use_it, who_its_for]
        if p and p.strip()
    ]
    return "\n".join(parts)


def embed_tool_fields(
    title: str = "",
    summary: str = "",
    what_it_does: str = "",
    when_to_use_it: str = "",
    who_its_for: str = "",
) -> list[float]:
    """Convenience wrapper: build text from fields, then generate embedding."""
    text = build_embedding_text(title, summary, what_it_does, when_to_use_it, who_its_for)
    return generate_embedding(text)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def store_embedding(tool_id: str, embedding: list[float]) -> None:
    """Write an embedding vector to the ``tools`` table for the given tool.

    Uses a raw SQL UPDATE so the vector is stored as a pgvector literal.
    """
    vector_literal = "[" + ",".join(str(v) for v in embedding) + "]"

    conn = psycopg2.connect(DATABASE_URL_SYNC)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE tools SET embedding = %s::vector, updated_at = now() WHERE id = %s;",
            (vector_literal, tool_id),
        )
        conn.commit()
        cur.close()
        logger.info("Stored embedding for tool %s", tool_id)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def generate_and_store(tool_id: str, **text_fields) -> list[float]:
    """Generate an embedding from text fields and store it in the DB.

    Keyword arguments are forwarded to :func:`embed_tool_fields`.

    Returns the embedding vector.
    """
    embedding = embed_tool_fields(**text_fields)
    store_embedding(tool_id, embedding)
    return embedding


# ---------------------------------------------------------------------------
# Backfill
# ---------------------------------------------------------------------------


def backfill_embeddings(force: bool = False) -> dict:
    """Generate and store embeddings for all tools that are missing one.

    Args:
        force: If ``True``, regenerate embeddings even for tools that
               already have one.

    Returns:
        A summary dict with counts of updated, skipped, and failed tools.
    """
    where = "" if force else "WHERE embedding IS NULL"

    conn = psycopg2.connect(DATABASE_URL_SYNC)
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, title, summary, what_it_does, when_to_use_it, who_its_for "
            f"FROM tools {where} ORDER BY title;"
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    total = len(rows)
    updated = 0
    skipped = 0
    failed = 0

    print(f"Backfilling embeddings for {total} tool(s)...")

    for i, (tool_id, title, summary, what_it_does, when_to_use_it, who_its_for) in enumerate(rows, 1):
        try:
            text = build_embedding_text(
                title=title or "",
                summary=summary or "",
                what_it_does=what_it_does or "",
                when_to_use_it=when_to_use_it or "",
                who_its_for=who_its_for or "",
            )
            if not text.strip():
                print(f"  [{i}/{total}] {title} -> skipped (no text)")
                skipped += 1
                continue

            start = time.time()
            embedding = generate_embedding(text)
            store_embedding(str(tool_id), embedding)
            elapsed = int((time.time() - start) * 1000)

            print(f"  [{i}/{total}] {title} -> embedded ({elapsed}ms)")
            updated += 1

        except Exception as exc:
            print(f"  [{i}/{total}] {title} -> FAILED: {exc}")
            logger.exception("Failed to embed tool %s", tool_id)
            failed += 1

    summary_dict = {
        "total": total,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
    }
    print(f"\nBackfill complete: {updated} updated, {skipped} skipped, {failed} failed")
    return summary_dict
