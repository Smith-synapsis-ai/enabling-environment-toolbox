"""Durable business tables in Postgres: analytics_events + token_usage (C6 Wave A).

Revision ID: 007_durable_business_tables
Revises: 006_content_governance
Create Date: 2026-06-13

WHY (decision 5 — the non-negotiable durability bar)
----------------------------------------------------
The anonymous business tables the admin dashboard reads (analytics_events =
C3 feature usage + C4 KPI access events + C5 pulse-survey rows) lived ONLY in
the ephemeral SQLite agent_store.db, which is destroyed on every ASG instance
replacement. This migration moves them to Postgres RDS, which already survives
replacement and which the dashboard already reads. It also creates the new
token_usage table (C6 / Thread 2) in the same durable store.

Purely additive: new tables only. Existing data untouched. Idempotent via
IF NOT EXISTS so re-runs (and the entrypoint `alembic upgrade head` on every
boot) are safe. The tiny pre-existing SQLite rows are backfilled separately at
app startup (persistence.backfill.backfill_sqlite_to_postgres), not here, so
the migration stays pure-DDL and never depends on a SQLite file being present.
"""

from alembic import op

# revision identifiers
revision = "007_durable_business_tables"
down_revision = "006_content_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- analytics_events (C3/C4/C5) -- shape identical to the legacy SQLite table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_events (
            id          BIGSERIAL PRIMARY KEY,
            event_name  TEXT NOT NULL,
            session_id  TEXT,
            created_at  TEXT,
            payload     JSONB
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_analytics_events_name "
        "ON analytics_events (event_name, created_at)"
    )

    # -- token_usage (C6 / Thread 2) -- one row per (session_id, turn) ResultMessage
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS token_usage (
            id                     BIGSERIAL PRIMARY KEY,
            session_id             TEXT,
            turn                   INTEGER,
            created_at             TEXT,
            orchestrator_model     TEXT,
            subagent_model         TEXT,
            num_turns              INTEGER,
            duration_ms            INTEGER,
            input_tokens           INTEGER,
            output_tokens          INTEGER,
            cache_read_tokens      INTEGER,
            cache_creation_tokens  INTEGER,
            total_cost_usd         DOUBLE PRECISION,
            is_error               BOOLEAN DEFAULT FALSE
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_token_usage_created_at "
        "ON token_usage (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_token_usage_session_turn "
        "ON token_usage (session_id, turn)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS token_usage")
    op.execute("DROP TABLE IF EXISTS analytics_events")
