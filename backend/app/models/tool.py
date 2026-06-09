import uuid
from datetime import date, datetime

from sqlalchemy import (
    Text,
    Date,
    Boolean,
    Integer,
    Numeric,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.models import Base


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    what_it_does: Mapped[str | None] = mapped_column(Text)
    when_to_use_it: Mapped[str | None] = mapped_column(Text)
    who_its_for: Mapped[str | None] = mapped_column(Text)

    pillars: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    domains: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    type: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str | None] = mapped_column(Text)
    target_users: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    geography: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    authors: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    date_published: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_organization: Mapped[str | None] = mapped_column(Text)
    cover_image_url: Mapped[str | None] = mapped_column(Text)

    embedding = mapped_column(Vector(1536), nullable=True)

    average_rating: Mapped[float] = mapped_column(
        Numeric(3, 2), server_default="0", nullable=False
    )
    rating_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    view_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )

    cgspace_id: Mapped[str | None] = mapped_column(Text, unique=True)
    relevance_score: Mapped[float | None] = mapped_column(Numeric(3, 2))
    is_visible: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    needs_review: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Note: Full-text search index on title+summary is created in the migration
    # as a GIN index on to_tsvector('english', ...). No model column needed.

    __table_args__ = (
        Index("ix_tools_pillars", "pillars", postgresql_using="gin"),
        Index("ix_tools_domains", "domains", postgresql_using="gin"),
        Index("ix_tools_target_users", "target_users", postgresql_using="gin"),
        Index("ix_tools_geography", "geography", postgresql_using="gin"),
        Index("ix_tools_type", "type"),
        Index("ix_tools_stage", "stage"),
        Index(
            "ix_tools_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
