"""Semantic similarity search for the Enabling Environment Toolbox.

Embeds a natural-language query with the same OpenAI model used for tool
embeddings, then queries pgvector using cosine distance (``<=>``) to
return the most similar tools.

All functions are synchronous, consistent with the rest of the pipeline
package.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import psycopg2
import psycopg2.extras

from pipeline.config import DATABASE_URL_SYNC
from pipeline.embeddings import EMBEDDING_MODEL, generate_embedding

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single tool returned by a similarity search."""

    tool_id: str
    title: str
    summary: Optional[str]
    what_it_does: Optional[str]
    when_to_use_it: Optional[str]
    who_its_for: Optional[str]
    pillars: list[str]
    domains: list[str]
    type: Optional[str]
    stage: Optional[str]
    target_users: list[str]
    geography: list[str]
    source_url: Optional[str]
    similarity: float  # 1.0 = identical, 0.0 = orthogonal


# ---------------------------------------------------------------------------
# Search functions
# ---------------------------------------------------------------------------


def similarity_search(
    query: str,
    top_n: int = 5,
    min_similarity: float = 0.0,
) -> list[SearchResult]:
    """Search for tools semantically similar to a natural-language query.

    Args:
        query: The user's natural-language search text.
        top_n: Maximum number of results to return.
        min_similarity: Minimum cosine similarity threshold (0.0–1.0).
                        Results below this score are excluded.

    Returns:
        A list of :class:`SearchResult` ordered by descending similarity.
    """
    logger.info("Embedding query: %s", query[:80])
    query_vector = generate_embedding(query)
    vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

    conn = psycopg2.connect(DATABASE_URL_SYNC)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT
                id,
                title,
                summary,
                what_it_does,
                when_to_use_it,
                who_its_for,
                pillars,
                domains,
                type,
                stage,
                target_users,
                geography,
                source_url,
                1 - (embedding <=> %s::vector) AS similarity
            FROM tools
            WHERE embedding IS NOT NULL
              AND is_visible = true
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """,
            (vector_literal, vector_literal, top_n),
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    results = []
    for row in rows:
        sim = float(row["similarity"])
        if sim < min_similarity:
            continue
        results.append(
            SearchResult(
                tool_id=str(row["id"]),
                title=row["title"],
                summary=row["summary"],
                what_it_does=row["what_it_does"],
                when_to_use_it=row["when_to_use_it"],
                who_its_for=row["who_its_for"],
                pillars=row["pillars"] or [],
                domains=row["domains"] or [],
                type=row["type"],
                stage=row["stage"],
                target_users=row["target_users"] or [],
                geography=row["geography"] or [],
                source_url=row["source_url"],
                similarity=sim,
            )
        )

    return results


def print_search_results(query: str, results: list[SearchResult]) -> None:
    """Pretty-print search results to stdout."""
    print(f'\nQuery: "{query}"')
    print("-" * 70)
    if not results:
        print("  No results found.")
        return

    for i, r in enumerate(results, 1):
        print(f"  {i}. {r.title}  (similarity: {r.similarity:.4f})")
        print(f"     Type: {r.type or '—'}  |  Stage: {r.stage or '—'}")
        print(f"     Pillars: {', '.join(r.pillars) if r.pillars else '—'}")
        print(f"     Domains: {', '.join(r.domains) if r.domains else '—'}")
        if r.summary:
            # Truncate long summaries for readability
            summary_display = r.summary[:150] + "..." if len(r.summary) > 150 else r.summary
            print(f"     Summary: {summary_display}")
        print()
