import uuid
from datetime import datetime

from sqlalchemy import Text, Integer, Boolean, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[str | None] = mapped_column(Text)
    query_text: Mapped[str | None] = mapped_column(Text)
    query_type: Mapped[str | None] = mapped_column(Text)  # 'semantic', 'faceted', 'chat'
    filters_used = mapped_column(JSONB, nullable=True)
    results_count: Mapped[int | None] = mapped_column(Integer)
    results_tool_ids = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_search_logs_created", "created_at"),
        Index("ix_search_logs_query_type", "query_type"),
    )


class ToolView(Base):
    __tablename__ = "tool_views"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tools.id"), nullable=False
    )
    session_id: Mapped[str | None] = mapped_column(Text)
    referrer: Mapped[str | None] = mapped_column(Text)  # 'search', 'chat', 'catalog', 'direct'
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    search_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_logs.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_tool_views_created", "created_at"),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    user_email: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(Text)
    user_type: Mapped[str | None] = mapped_column(Text, server_default="unknown")
    utm_source: Mapped[str | None] = mapped_column(Text)
    utm_medium: Mapped[str | None] = mapped_column(Text)
    utm_campaign: Mapped[str | None] = mapped_column(Text)
    is_bot: Mapped[bool | None] = mapped_column(Boolean, server_default="false")

    __table_args__ = (
        Index("ix_user_sessions_started", "started_at"),
    )


class EmailCapture(Base):
    __tablename__ = "email_captures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text, server_default="modal")
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
