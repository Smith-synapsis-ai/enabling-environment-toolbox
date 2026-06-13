"""Seed original 92 tools from seeds/seed.sql.

Revision ID: 005_seed_92_tools
Revises: 004_seed_missing_8_tools
Create Date: 2026-06-12

Context
-------
The initial seed.sql (92 higher-quality tools) was applied manually to the
development/management-account RDS instance but was never run against the
production RDS instance, which only received Alembic migrations.  The prod DB
therefore only has the 8 tools inserted by migration 004.

This migration applies all 92 tools idempotently so that total tools = 100.

Approach
--------
* The seed.sql file is stored at backend/alembic/seeds/seed.sql so it is
  included in the Docker image (Dockerfile: COPY backend/ /app/backend/).
* We extract the 92 INSERT INTO public.tools statements via regex and
  append ON CONFLICT (cgspace_id) DO NOTHING to each, making the migration
  safe to re-run.
* We use the raw psycopg2 DBAPI cursor (conn.connection.cursor()) and call
  cur.execute(sql) with a SINGLE argument — no params object.  This is
  critical: psycopg2 performs % interpolation only when a params argument is
  supplied, so literal "%" chars in seed values (e.g. "60% of agricultural
  labor") pass through untouched.  SQLAlchemy's exec_driver_sql() always
  passes an immutabledict as params, which causes a TypeError in the Cython
  build; the raw cursor sidesteps both issues.
* The seeding is wrapped in a broad except so an unexpected error in the
  data-seed step never crash-loops the application — a partial or empty
  catalog is far preferable to a hard 502.
"""

import re
import traceback
from pathlib import Path

from alembic import op

# revision identifiers
revision = "005_seed_92_tools"
down_revision = "004_seed_missing_8_tools"
branch_labels = None
depends_on = None

# seed.sql lives next to this file's parent directory:
#   /app/backend/alembic/versions/005_seed_92_tools.py  →  parents[1] = /app/backend/alembic/
_SEED_PATH = Path(__file__).resolve().parents[1] / "seeds" / "seed.sql"

# Match each INSERT INTO public.tools ... VALUES (...);  (may span lines)
_PATTERN = re.compile(
    r"(INSERT INTO public\.tools \([^)]+\) VALUES \(.*?\));",
    re.DOTALL,
)


def upgrade() -> None:
    try:
        seed_sql = _SEED_PATH.read_text(encoding="utf-8")
        matches = _PATTERN.findall(seed_sql)

        if not matches:
            print(
                f"005_seed_92_tools: WARNING — no INSERT INTO public.tools statements "
                f"found in {_SEED_PATH}. Skipping seed step; app will still start."
            )
            return

        conn = op.get_bind()
        # Use the raw psycopg2 DBAPI connection so we can call cur.execute(sql)
        # with a single argument.  conn.connection is a PoolProxiedConnection that
        # exposes a cursor() method backed by the real psycopg2 connection.
        dbapi_conn = conn.connection
        cur = dbapi_conn.cursor()
        count = 0
        for stmt in matches:
            idempotent = stmt + " ON CONFLICT (cgspace_id) DO NOTHING"
            cur.execute(idempotent)
            count += 1
        cur.close()

        print(f"005_seed_92_tools: inserted/skipped {count} tool records")

    except Exception:
        print(
            "005_seed_92_tools: ERROR during seed — logging and continuing so the "
            "app can still start.  Catalog may be empty or partial."
        )
        traceback.print_exc()


def downgrade() -> None:
    # Non-destructive: do not delete seeded records on downgrade
    pass
