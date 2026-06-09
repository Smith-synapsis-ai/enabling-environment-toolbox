"""Pulse survey responses table and needs_review column on tools.

Revision ID: 003_pulse_survey
Revises: 002_analytics
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = "003_pulse_survey"
down_revision = "002_analytics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # NEW TABLE: pulse_survey_responses
    # ------------------------------------------------------------------ #
    op.create_table(
        "pulse_survey_responses",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("question_key", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "score >= 1 AND score <= 5", name="ck_pulse_survey_score_range"
        ),
    )
    op.create_index(
        "ix_pulse_survey_session",
        "pulse_survey_responses",
        ["session_id"],
    )
    op.create_index(
        "ix_pulse_survey_question",
        "pulse_survey_responses",
        ["question_key"],
    )

    # ------------------------------------------------------------------ #
    # COLUMN ADDITION to tools table
    # ------------------------------------------------------------------ #
    op.add_column(
        "tools",
        sa.Column("needs_review", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    # Drop needs_review from tools
    op.drop_column("tools", "needs_review")

    # Drop indexes and table for pulse_survey_responses
    op.drop_index("ix_pulse_survey_question", table_name="pulse_survey_responses")
    op.drop_index("ix_pulse_survey_session", table_name="pulse_survey_responses")
    op.drop_table("pulse_survey_responses")
