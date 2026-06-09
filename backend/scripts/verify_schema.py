"""Verify the EE Toolbox database schema is correctly set up.

Checks:
1. All expected tables exist
2. pgvector extension is loaded
3. Can insert a tool with a vector embedding
4. Can query by vector similarity
5. Partial unique index on prompt_versions works
"""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text, inspect
from app.database import sync_engine, SyncSessionLocal

EXPECTED_TABLES = [
    "tools",
    "user_ratings",
    "search_logs",
    "tool_views",
    "user_sessions",
    "email_captures",
    "prompt_versions",
    "prompt_eval_results",
]


def check_tables():
    inspector = inspect(sync_engine)
    existing = inspector.get_table_names()
    all_ok = True
    for table in EXPECTED_TABLES:
        if table in existing:
            print(f"  [OK] Table '{table}' exists")
        else:
            print(f"  [FAIL] Table '{table}' NOT FOUND")
            all_ok = False
    return all_ok


def check_pgvector():
    with sync_engine.connect() as conn:
        result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        row = result.fetchone()
        if row:
            print("  [OK] pgvector extension is loaded")
            return True
        else:
            print("  [FAIL] pgvector extension NOT loaded")
            return False


def check_vector_operations():
    """Insert a tool with an embedding and verify similarity search works."""
    import random
    random.seed(42)

    # Generate two test embeddings (1536 dimensions)
    embedding_a = [random.gauss(0, 1) for _ in range(1536)]
    embedding_b = [random.gauss(0, 1) for _ in range(1536)]

    with SyncSessionLocal() as session:
        # Clean up any test data from previous runs
        session.execute(text("DELETE FROM tools WHERE cgspace_id LIKE 'test-verify-%'"))
        session.commit()

        # Insert two test tools with embeddings
        id_a = uuid.uuid4()
        id_b = uuid.uuid4()

        session.execute(
            text(
                "INSERT INTO tools (id, title, cgspace_id, embedding) "
                "VALUES (:id, :title, :cgspace_id, :embedding)"
            ),
            {
                "id": str(id_a),
                "title": "Test Tool A",
                "cgspace_id": "test-verify-a",
                "embedding": str(embedding_a),
            },
        )
        session.execute(
            text(
                "INSERT INTO tools (id, title, cgspace_id, embedding) "
                "VALUES (:id, :title, :cgspace_id, :embedding)"
            ),
            {
                "id": str(id_b),
                "title": "Test Tool B",
                "cgspace_id": "test-verify-b",
                "embedding": str(embedding_b),
            },
        )
        session.commit()
        print("  [OK] Inserted 2 test tools with 1536-dim embeddings")

        # Query by cosine similarity (should return Tool A first when queried with its own embedding)
        result = session.execute(
            text(
                "SELECT title, embedding <=> :query_vec AS distance "
                "FROM tools "
                "WHERE cgspace_id LIKE 'test-verify-%' "
                "ORDER BY embedding <=> :query_vec "
                "LIMIT 2"
            ),
            {"query_vec": str(embedding_a)},
        )
        rows = result.fetchall()

        if len(rows) == 2 and rows[0][0] == "Test Tool A" and rows[0][1] == 0.0:
            print(f"  [OK] Vector similarity search works (nearest: '{rows[0][0]}', distance: {rows[0][1]:.4f})")
            vector_ok = True
        else:
            print(f"  [FAIL] Unexpected similarity results: {rows}")
            vector_ok = False

        # Clean up test data
        session.execute(text("DELETE FROM tools WHERE cgspace_id LIKE 'test-verify-%'"))
        session.commit()
        print("  [OK] Cleaned up test data")

        return vector_ok


def check_indexes():
    """Verify key indexes exist."""
    with sync_engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT indexname FROM pg_indexes WHERE tablename IN ('tools', 'prompt_versions') "
                "ORDER BY indexname"
            )
        )
        indexes = [row[0] for row in result.fetchall()]

    expected_indexes = [
        "ix_tools_pillars",
        "ix_tools_domains",
        "ix_tools_target_users",
        "ix_tools_geography",
        "ix_tools_type",
        "ix_tools_stage",
        "ix_tools_embedding",
        "ix_tools_fulltext",
        "ix_prompt_active_unique",
    ]

    all_ok = True
    for idx in expected_indexes:
        if idx in indexes:
            print(f"  [OK] Index '{idx}' exists")
        else:
            print(f"  [FAIL] Index '{idx}' NOT FOUND")
            all_ok = False

    return all_ok


def check_prompt_unique_constraint():
    """Verify the partial unique index prevents two active prompts with the same name."""
    with SyncSessionLocal() as session:
        # Clean up
        session.execute(text("DELETE FROM prompt_versions WHERE created_by = 'verify_test'"))
        session.commit()

        # Insert one active prompt
        session.execute(
            text(
                "INSERT INTO prompt_versions (prompt_name, version, prompt_text, is_active, created_by) "
                "VALUES ('_test_unique', 1, 'test prompt 1', true, 'verify_test')"
            )
        )
        session.commit()

        # Try to insert a second active prompt with the same name -- should fail
        try:
            session.execute(
                text(
                    "INSERT INTO prompt_versions (prompt_name, version, prompt_text, is_active, created_by) "
                    "VALUES ('_test_unique', 2, 'test prompt 2', true, 'verify_test')"
                )
            )
            session.commit()
            print("  [FAIL] Partial unique index did NOT prevent two active prompts with same name")
            ok = False
        except Exception:
            session.rollback()
            print("  [OK] Partial unique index correctly prevents two active prompts with same name")
            ok = True

        # Clean up
        session.execute(text("DELETE FROM prompt_versions WHERE created_by = 'verify_test'"))
        session.commit()
        return ok


def main():
    print("=" * 60)
    print("EE Toolbox — Schema Verification")
    print("=" * 60)

    results = {}

    print("\n1. Checking tables...")
    results["tables"] = check_tables()

    print("\n2. Checking pgvector extension...")
    results["pgvector"] = check_pgvector()

    print("\n3. Checking indexes...")
    results["indexes"] = check_indexes()

    print("\n4. Checking vector insert + similarity query...")
    results["vector_ops"] = check_vector_operations()

    print("\n5. Checking prompt active uniqueness constraint...")
    results["prompt_unique"] = check_prompt_unique_constraint()

    print("\n" + "=" * 60)
    all_passed = all(results.values())
    if all_passed:
        print("ALL CHECKS PASSED")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"FAILED CHECKS: {', '.join(failed)}")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
