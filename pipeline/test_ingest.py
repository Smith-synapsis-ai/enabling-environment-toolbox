"""Integration test for the end-to-end ingestion pipeline.

Selects a small mix of relevant and irrelevant items from the test data,
runs ingest_batch(), then queries the tools table to verify that relevant
items were stored correctly.

Usage:
    python -m pipeline.test_ingest
"""

import json
import sys

import psycopg2
import psycopg2.extras

from pipeline.config import DATABASE_URL_SYNC
from pipeline.ingest import ingest_batch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_DATA_PATH = "/Users/smithai/workspace/ee-toolbox-app/pipeline/test_data/relevance_test_set.json"

# Indices into relevance_test_set.json
RELEVANT_INDICES = [0, 2, 5]        # Scaling Scan, MELIA Framework, Digital Agriculture Assessment Tool
IRRELEVANT_TITLES = [
    "Genome-Wide Association Study for Rice Blast Resistance in Indica Cultivars",
    "Annual Report 2024: International Maize and Wheat Improvement Center",
]


def load_test_items() -> list[dict]:
    """Load the 5 specific test items from the relevance test set."""
    with open(TEST_DATA_PATH, "r") as f:
        full_set = json.load(f)

    items: list[dict] = []

    # Pick the three relevant items by index
    for idx in RELEVANT_INDICES:
        items.append(full_set[idx])

    # Pick the two irrelevant items by title
    for title in IRRELEVANT_TITLES:
        for entry in full_set:
            if entry["title"] == title:
                items.append(entry)
                break

    return items


def verify_stored_tools(expected_titles: list[str]):
    """Query the tools table and print stored records for verification."""
    conn = psycopg2.connect(DATABASE_URL_SYNC)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # Use ANY to match titles in the expected list
        cur.execute(
            "SELECT id, title, summary, what_it_does, when_to_use_it, who_its_for, "
            "       pillars, domains, type, stage, target_users, geography, "
            "       authors, date_published, source_url, cgspace_id, relevance_score, "
            "       is_visible, created_at, updated_at "
            "FROM tools WHERE title = ANY(%s) ORDER BY title;",
            (expected_titles,),
        )
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main test routine
# ---------------------------------------------------------------------------


def run_test():
    """Execute the integration test and print a detailed report."""
    print("=" * 72)
    print("EE TOOLBOX INGESTION PIPELINE -- INTEGRATION TEST")
    print("=" * 72)

    # Load test items
    items = load_test_items()
    print(f"\nLoaded {len(items)} test items:")
    for i, item in enumerate(items):
        expected = "relevant" if item.get("expected_relevant") else "irrelevant"
        print(f"  {i + 1}. [{expected:>10s}] {item['title']}")
    print()

    # Run the batch
    print("-" * 72)
    print("RUNNING INGESTION BATCH")
    print("-" * 72)
    batch = ingest_batch(items)
    print()

    # Per-item results
    print("-" * 72)
    print("PER-ITEM RESULTS")
    print("-" * 72)
    for r in batch.results:
        print(f"\n  Title:       {r.title}")
        print(f"  Status:      {r.status}")
        print(f"  Tool ID:     {r.tool_id or '(none)'}")
        print(f"  Confidence:  {r.relevance_confidence:.2f}")
        print(f"  Reasoning:   {r.relevance_reasoning[:120]}")
        print(f"  Latency:     {r.total_latency_ms} ms")
        print(f"  Stages:      {', '.join(r.stages_completed)}")
        if r.extraction_warnings:
            print(f"  Warnings:    {r.extraction_warnings}")
        if r.error:
            print(f"  Error:       {r.error}")

    # Database verification
    print()
    print("-" * 72)
    print("DATABASE VERIFICATION")
    print("-" * 72)

    stored_titles = [r.title for r in batch.results if r.status == "stored"]
    if stored_titles:
        rows = verify_stored_tools(stored_titles)
        print(f"\nFound {len(rows)} record(s) in tools table:\n")
        for row in rows:
            print(f"  --- {row['title']} ---")
            for key, value in row.items():
                if key == "title":
                    continue
                display = value
                if isinstance(value, list) and len(value) > 3:
                    display = value[:3] + ["..."]
                print(f"    {key:22s}: {display}")
            print()
    else:
        print("\n  No tools were stored (nothing to verify).\n")

    # Summary
    print("=" * 72)
    print("BATCH SUMMARY")
    print("=" * 72)
    print(f"  Total processed:  {batch.total}")
    print(f"  Stored:           {batch.stored}")
    print(f"  Skipped:          {batch.skipped}")
    print(f"  Failed:           {batch.failed}")
    print(f"  Elapsed:          {batch.elapsed_seconds:.1f}s")

    # Correctness check -- did irrelevant items get skipped?
    expected_skipped = [r for r in batch.results if r.title in IRRELEVANT_TITLES]
    all_irrelevant_skipped = all(r.status == "skipped_irrelevant" for r in expected_skipped)

    expected_stored = [r for r in batch.results if r.title not in IRRELEVANT_TITLES]
    all_relevant_stored = all(r.status == "stored" for r in expected_stored)

    print()
    if all_irrelevant_skipped and all_relevant_stored:
        print("  RESULT: PASS -- all relevant items stored, all irrelevant items skipped.")
    else:
        print("  RESULT: ISSUES DETECTED")
        for r in expected_skipped:
            if r.status != "skipped_irrelevant":
                print(f"    Expected skip but got '{r.status}': {r.title}")
        for r in expected_stored:
            if r.status != "stored":
                print(f"    Expected stored but got '{r.status}': {r.title}")

    print("=" * 72)


if __name__ == "__main__":
    run_test()
