"""Analytics enhancements: conversation_turns, rating_events, admin_tokens,
tool_saves, and column additions to existing tables.

Revision ID: 002_analytics
Revises: 001_initial
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

# revision identifiers
revision = "002_analytics"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # NEW TABLE: conversation_turns
    # ------------------------------------------------------------------ #
    op.create_table(
        "conversation_turns",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("conversation_id", sa.Text(), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "recommended_tool_ids",
            ARRAY(UUID(as_uuid=True)),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("search_query", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')", name="ck_conversation_turns_role"
        ),
    )
    op.create_index(
        "ix_conversation_turns_conv_id",
        "conversation_turns",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_turns_session",
        "conversation_turns",
        ["session_id"],
    )

    # ------------------------------------------------------------------ #
    # NEW TABLE: rating_events
    # ------------------------------------------------------------------ #
    op.create_table(
        "rating_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "tool_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("user_identifier", sa.Text(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5", name="ck_rating_events_range"
        ),
    )
    op.create_index("ix_rating_events_tool", "rating_events", ["tool_id"])
    op.create_index("ix_rating_events_created", "rating_events", ["created_at"])

    # ------------------------------------------------------------------ #
    # NEW TABLE: admin_tokens
    # ------------------------------------------------------------------ #
    op.create_table(
        "admin_tokens",
        sa.Column("token", UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=False
        ),
    )

    # ------------------------------------------------------------------ #
    # NEW TABLE: tool_saves
    # ------------------------------------------------------------------ #
    op.create_table(
        "tool_saves",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column(
            "tool_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("session_id", "tool_id", name="uq_tool_save_session_tool"),
    )
    op.create_index("ix_tool_saves_session", "tool_saves", ["session_id"])
    op.create_index("ix_tool_saves_tool", "tool_saves", ["tool_id"])

    # ------------------------------------------------------------------ #
    # COLUMN ADDITIONS to existing tables
    # ------------------------------------------------------------------ #

    # email_captures: add session_id and source
    op.add_column(
        "email_captures", sa.Column("session_id", sa.Text(), nullable=True)
    )
    op.add_column(
        "email_captures",
        sa.Column("source", sa.Text(), server_default="modal", nullable=True),
    )

    # user_sessions: add user_type, utm_source, utm_medium, utm_campaign, is_bot
    op.add_column(
        "user_sessions",
        sa.Column("user_type", sa.Text(), server_default="unknown", nullable=True),
    )
    op.add_column(
        "user_sessions", sa.Column("utm_source", sa.Text(), nullable=True)
    )
    op.add_column(
        "user_sessions", sa.Column("utm_medium", sa.Text(), nullable=True)
    )
    op.add_column(
        "user_sessions", sa.Column("utm_campaign", sa.Text(), nullable=True)
    )
    op.add_column(
        "user_sessions",
        sa.Column("is_bot", sa.Boolean(), server_default="false", nullable=True),
    )

    # tool_views: add duration_seconds and search_log_id
    op.add_column(
        "tool_views", sa.Column("duration_seconds", sa.Integer(), nullable=True)
    )
    op.add_column(
        "tool_views",
        sa.Column(
            "search_log_id",
            UUID(as_uuid=True),
            sa.ForeignKey("search_logs.id"),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------ #
    # NEW INDEXES on existing tables
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_user_sessions_started", "user_sessions", ["started_at"]
    )
    op.create_index(
        "ix_search_logs_created", "search_logs", ["created_at"]
    )
    op.create_index(
        "ix_tool_views_created", "tool_views", ["created_at"]
    )
    op.create_index(
        "ix_search_logs_query_type", "search_logs", ["query_type"]
    )


def downgrade() -> None:
    # Drop new indexes on existing tables
    op.drop_index("ix_search_logs_query_type", table_name="search_logs")
    op.drop_index("ix_tool_views_created", table_name="tool_views")
    op.drop_index("ix_search_logs_created", table_name="search_logs")
    op.drop_index("ix_user_sessions_started", table_name="user_sessions")

    # Drop added columns from tool_views
    op.drop_column("tool_views", "search_log_id")
    op.drop_column("tool_views", "duration_seconds")

    # Drop added columns from user_sessions
    op.drop_column("user_sessions", "is_bot")
    op.drop_column("user_sessions", "utm_campaign")
    op.drop_column("user_sessions", "utm_medium")
    op.drop_column("user_sessions", "utm_source")
    op.drop_column("user_sessions", "user_type")

    # Drop added columns from email_captures
    op.drop_column("email_captures", "source")
    op.drop_column("email_captures", "session_id")

    # Drop new tables (reverse order of creation)
    op.drop_table("tool_saves")
    op.drop_table("admin_tokens")
    op.drop_table("rating_events")
    op.drop_table("conversation_turns")
