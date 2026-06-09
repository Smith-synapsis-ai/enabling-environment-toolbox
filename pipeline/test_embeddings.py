"""Test script for vector embeddings and semantic similarity search.

Backfills embeddings for all tools currently in the database, then runs
a set of natural-language queries to demonstrate semantic search.

Usage:
    python -m pipeline.test_embeddings
"""

import time

import psycopg2
from pipeline.config import DATABASE_URL_SYNC
from pipeline.embeddings import backfill_embeddings, EMBEDDING_MODEL, EMBEDDING_DIMENSION
from pipeline.search import similarity_search, print_search_results


TEST_QUERIES = [
    "how to include smallholder farmers in policy decisions",
    "monitoring and evaluation frameworks for agriculture",
    "digital tools for rural extension services",
    "scaling agricultural innovations in Africa",
    "gender equality assessment for development projects",
]


def check_embedding_status():
    """Print the embedding status of all tools in the database."""
    conn = psycopg2.connect(DATABASE_URL_SYNC)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT title, (embedding IS NOT NULL) as has_embedding "
            "FROM tools ORDER BY title;"
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    print(f"\nEmbedding status ({len(rows)} tools):")
    for title, has_emb in rows:
        status = "embedded" if has_emb else "MISSING"
        print(f"  [{status:>8s}] {title}")
    return rows


def main():
    print("=" * 72)
    print("EE TOOLBOX — VECTOR EMBEDDINGS & SIMILARITY SEARCH TEST")
    print("=" * 72)
    print(f"\nEmbedding model: {EMBEDDING_MODEL}")
    print(f"Vector dimension: {EMBEDDING_DIMENSION}")

    # ── Step 1: Check current state ──────────────────────────────────────
    print("\n" + "-" * 72)
    print("STEP 1: CURRENT EMBEDDING STATUS")
    print("-" * 72)
    rows = check_embedding_status()
    missing = sum(1 for _, has in rows if not has)

    # ── Step 2: Backfill ─────────────────────────────────────────────────
    if missing > 0:
        print(f"\n{missing} tool(s) need embeddings. Running backfill...\n")
        print("-" * 72)
        print("STEP 2: BACKFILL EMBEDDINGS")
        print("-" * 72)
        start = time.time()
        result = backfill_embeddings()
        elapsed = time.time() - start
        print(f"\nBackfill completed in {elapsed:.1f}s")
    else:
        print("\nAll tools already have embeddings. Skipping backfill.")

    # Verify
    print("\n" + "-" * 72)
    print("POST-BACKFILL STATUS")
    print("-" * 72)
    check_embedding_status()

    # ── Step 3: Similarity search ────────────────────────────────────────
    print("\n" + "=" * 72)
    print("STEP 3: SEMANTIC SIMILARITY SEARCH")
    print("=" * 72)

    for query in TEST_QUERIES:
        start = time.time()
        results = similarity_search(query, top_n=3)
        elapsed_ms = int((time.time() - start) * 1000)

        print_search_results(query, results)
        print(f"  (search latency: {elapsed_ms}ms)")
        print()

    # ── Summary ──────────────────────────────────────────────────────────
    print("=" * 72)
    print("TEST COMPLETE")
    print("=" * 72)
    print(f"  Model:      {EMBEDDING_MODEL}")
    print(f"  Dimension:  {EMBEDDING_DIMENSION}")
    print(f"  Queries:    {len(TEST_QUERIES)}")
    print(f"  Tools in DB: {len(rows)}")
    print("=" * 72)


if __name__ == "__main__":
    main()
