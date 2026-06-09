#!/usr/bin/env python3
"""
One-time seed data loader for EE Toolbox.

- Runs Alembic migrations (idempotent safety net)
- Checks if tools table already has data
- Strips psql meta-commands (\\restrict, \\unrestrict) from the dump
- Loads seed SQL via psycopg2
"""

import os
import sys
import subprocess

# Ensure the backend package is importable
sys.path.insert(0, "/app/backend")


def main():
    db_url = os.environ.get("DATABASE_URL_SYNC")
    if not db_url:
        print("ERROR: DATABASE_URL_SYNC environment variable not set")
        sys.exit(1)

    # ---- Step 1: Run Alembic migrations ----
    print("Step 1/3: Running Alembic migrations...")
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd="/app/backend",
    )
    if result.returncode != 0:
        print("ERROR: Alembic migration failed!")
        sys.exit(1)
    print("  Migrations complete.")

    # ---- Step 2: Check if data already exists ----
    import psycopg2

    print("Step 2/3: Checking existing data...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    try:
        cur.execute("SELECT count(*) FROM tools")
        count = cur.fetchone()[0]
        if count > 0:
            print(f"  Database already has {count} tools. Skipping seed.")
            conn.close()
            sys.exit(0)
    except Exception as e:
        print(f"  Warning: Could not check tools table ({e}). Will attempt to seed.")
        conn.rollback()

    # ---- Step 3: Load seed data ----
    print("Step 3/3: Loading seed data from /app/data/seed.sql ...")
    seed_path = "/app/data/seed.sql"
    if not os.path.exists(seed_path):
        print(f"ERROR: Seed file not found at {seed_path}")
        conn.close()
        sys.exit(1)

    with open(seed_path) as f:
        sql = f.read()

    # Strip psql meta-commands (lines starting with \)
    lines = sql.split("\n")
    clean_lines = [line for line in lines if not line.startswith("\\")]
    clean_sql = "\n".join(clean_lines)

    try:
        cur.execute(clean_sql)
        conn.commit()
    except Exception as e:
        print(f"ERROR: Failed to load seed data: {e}")
        conn.rollback()
        conn.close()
        sys.exit(1)

    # Verify
    cur.execute("SELECT count(*) FROM tools")
    tool_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM prompt_versions")
    prompt_count = cur.fetchone()[0]
    print(f"  Seed data loaded: {tool_count} tools, {prompt_count} prompt versions.")

    conn.close()
    print("=== Seeding complete! ===")


if __name__ == "__main__":
    main()
