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
* exec_driver_sql() is used instead of op.execute(text()) to bypass
  SQLAlchemy's parameter-placeholder parser, which would misinterpret colons
  in embedded values.
"""

import re
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
    seed_sql = _SEED_PATH.read_text(encoding="utf-8")
    matches = _PATTERN.findall(seed_sql)

    if not matches:
        raise RuntimeError(
            f"005_seed_92_tools: no INSERT INTO public.tools statements found in {_SEED_PATH}"
        )

    conn = op.get_bind()
    count = 0
    for stmt in matches:
        idempotent = stmt + " ON CONFLICT (cgspace_id) DO NOTHING"
        conn.exec_driver_sql(idempotent)
        count += 1

    print(f"005_seed_92_tools: inserted/skipped {count} tool records")


def downgrade() -> None:
    # Non-destructive: do not delete seeded records on downgrade
    pass
