"""Thumbnail pipeline job table (C6 Wave B / Thread 3).

Revision ID: 008_thumbnail_jobs
Revises: 007_durable_business_tables
Create Date: 2026-06-13

WHY
---
The AI-thumbnail pipeline (Jose feedback item 7) is operator-controlled,
budget-gated and REVIEWABLE: an admin triggers a small batch, the controlled
agent/CI path generates images and stages them in S3, the admin reviews the
staged grid and Approve/Reject/Regenerate per tool. Approve promotes the
staged image to the live S3 key and sets the tool's cover_image_url.

This table is the durable record of that workflow — one row per (tool) thumbnail
request. It lives in the same durable Postgres store as the other C6 business
tables (survives ASG instance replacement). Purely additive; idempotent via
IF NOT EXISTS so the entrypoint `alembic upgrade head` on every boot is safe.

Status lifecycle:
    requested  -> a batch trigger enqueued this tool for generation
    generating -> the controlled path picked it up (optional transient)
    staged     -> a thumbnail exists at thumbnails-staging/<cgspace_id>.png
    approved   -> promoted to thumbnails/<cgspace_id>.png + cover_image_url set
    rejected   -> operator rejected the staged image
    failed     -> generation/upload failed (detail in error)
"""

from alembic import op

# revision identifiers
revision = "008_thumbnail_jobs"
down_revision = "007_durable_business_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS thumbnail_jobs (
            id            BIGSERIAL PRIMARY KEY,
            batch_id      TEXT NOT NULL,
            cgspace_id    TEXT NOT NULL,
            tool_title    TEXT,
            prompt        TEXT,
            status        TEXT NOT NULL DEFAULT 'requested',
            staging_key   TEXT,
            live_key      TEXT,
            staging_url   TEXT,
            live_url      TEXT,
            cost_usd      DOUBLE PRECISION,
            error         TEXT,
            requested_by  TEXT,
            requested_at  TEXT,
            updated_at    TEXT
        )
        """
    )
    # One active (non-rejected) job per tool keeps the review grid clean; we
    # enforce uniqueness on (cgspace_id) for the LATEST row via app logic, but
    # index for fast lookups by tool and by batch/status.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_thumbnail_jobs_cgspace "
        "ON thumbnail_jobs (cgspace_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_thumbnail_jobs_batch_status "
        "ON thumbnail_jobs (batch_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_thumbnail_jobs_status "
        "ON thumbnail_jobs (status, requested_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS thumbnail_jobs")
