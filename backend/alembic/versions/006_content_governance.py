"""Add content governance: content_proposals table and tools.last_verified_at column.

Revision ID: 006_content_governance
Revises: 005_seed_92_tools
Create Date: 2026-06-13

This migration is purely additive:
  - Creates a new `content_proposals` table (append-only moderation queue).
  - Adds a nullable `last_verified_at` TIMESTAMPTZ column to `tools`.

Zero risk to existing data: existing tool rows get last_verified_at = NULL
(correct — not yet verified via the governance pipeline). The live catalog
(is_visible=true filter) is completely unaffected.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "006_content_governance"
down_revision = "005_seed_92_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add last_verified_at to tools (nullable, all existing rows get NULL)
    op.add_column(
        "tools",
        sa.Column("last_verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # 2. Create the content_proposals table
    op.execute(
        """
        CREATE TABLE content_proposals (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tool_id         UUID REFERENCES tools(id) ON DELETE SET NULL,
            proposal_type   TEXT NOT NULL DEFAULT 'edit',
            submitted_by    TEXT,
            provenance      TEXT,
            proposed_fields JSONB NOT NULL,
            status          TEXT NOT NULL DEFAULT 'pending',
            reviewer_notes  TEXT,
            reviewed_by     TEXT,
            submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            reviewed_at     TIMESTAMPTZ
        )
        """
    )

    # 3. Indexes for admin dashboard queries
    op.execute(
        "CREATE INDEX ix_proposals_status ON content_proposals (status)"
    )
    op.execute(
        "CREATE INDEX ix_proposals_tool_id ON content_proposals (tool_id)"
    )
    op.execute(
        "CREATE INDEX ix_proposals_submitted_at ON content_proposals (submitted_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content_proposals")
    op.drop_column("tools", "last_verified_at")
