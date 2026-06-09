"""Initial schema - all tables for EE Toolbox

Revision ID: 001_initial
Revises:
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector

# revision identifiers
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ---------- tools ----------
    op.create_table(
        "tools",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("what_it_does", sa.Text(), nullable=True),
        sa.Column("when_to_use_it", sa.Text(), nullable=True),
        sa.Column("who_its_for", sa.Text(), nullable=True),
        sa.Column("pillars", ARRAY(sa.Text()), nullable=True),
        sa.Column("domains", ARRAY(sa.Text()), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("stage", sa.Text(), nullable=True),
        sa.Column("target_users", ARRAY(sa.Text()), nullable=True),
        sa.Column("geography", ARRAY(sa.Text()), nullable=True),
        sa.Column("authors", ARRAY(sa.Text()), nullable=True),
        sa.Column("date_published", sa.Date(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_organization", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("average_rating", sa.Numeric(3, 2), server_default="0", nullable=False),
        sa.Column("rating_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("view_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cgspace_id", sa.Text(), unique=True, nullable=True),
        sa.Column("relevance_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("is_visible", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # GIN indexes for array columns
    op.create_index("ix_tools_pillars", "tools", ["pillars"], postgresql_using="gin")
    op.create_index("ix_tools_domains", "tools", ["domains"], postgresql_using="gin")
    op.create_index("ix_tools_target_users", "tools", ["target_users"], postgresql_using="gin")
    op.create_index("ix_tools_geography", "tools", ["geography"], postgresql_using="gin")

    # B-tree indexes
    op.create_index("ix_tools_type", "tools", ["type"])
    op.create_index("ix_tools_stage", "tools", ["stage"])

    # HNSW vector index for cosine similarity search
    op.execute(
        "CREATE INDEX ix_tools_embedding ON tools USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64)"
    )

    # Full-text search index on title + summary
    op.execute(
        "CREATE INDEX ix_tools_fulltext ON tools USING gin ("
        "to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, ''))"
        ")"
    )

    # ---------- user_ratings ----------
    op.create_table(
        "user_ratings",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tool_id", UUID(as_uuid=True), sa.ForeignKey("tools.id"), nullable=False),
        sa.Column("user_identifier", sa.Text(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("tool_id", "user_identifier", name="uq_rating_tool_user"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_rating_range"),
    )

    # ---------- search_logs ----------
    op.create_table(
        "search_logs",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("query_type", sa.Text(), nullable=True),
        sa.Column("filters_used", JSONB(), nullable=True),
        sa.Column("results_count", sa.Integer(), nullable=True),
        sa.Column("results_tool_ids", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ---------- tool_views ----------
    op.create_table(
        "tool_views",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tool_id", UUID(as_uuid=True), sa.ForeignKey("tools.id"), nullable=False),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ---------- user_sessions ----------
    op.create_table(
        "user_sessions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("session_id", sa.Text(), unique=True, nullable=False),
        sa.Column("user_email", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
    )

    # ---------- email_captures ----------
    op.create_table(
        "email_captures",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.Text(), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ---------- prompt_versions ----------
    op.create_table(
        "prompt_versions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("prompt_name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=True),
        sa.UniqueConstraint("prompt_name", "version", name="uq_prompt_name_version"),
    )

    # Partial unique index: only one active prompt per prompt_name
    op.execute(
        "CREATE UNIQUE INDEX ix_prompt_active_unique ON prompt_versions (prompt_name) "
        "WHERE is_active = true"
    )

    # ---------- prompt_eval_results ----------
    op.create_table(
        "prompt_eval_results",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("prompt_version_id", UUID(as_uuid=True), sa.ForeignKey("prompt_versions.id"), nullable=False),
        sa.Column("input_data", JSONB(), nullable=True),
        sa.Column("output_data", JSONB(), nullable=True),
        sa.Column("expected_output", JSONB(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Numeric(5, 4), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.Text(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evaluated_by", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("prompt_eval_results")
    op.drop_table("prompt_versions")
    op.drop_table("email_captures")
    op.drop_table("user_sessions")
    op.drop_table("tool_views")
    op.drop_table("search_logs")
    op.drop_table("user_ratings")
    op.drop_table("tools")
    op.execute("DROP EXTENSION IF EXISTS vector")
