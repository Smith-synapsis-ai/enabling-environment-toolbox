"""ToolSave model — tracks tools saved/favorited by users."""

import uuid
from datetime import datetime

from sqlalchemy import Text, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ToolSave(Base):
    __tablename__ = "tool_saves"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("session_id", "tool_id", name="uq_tool_save_session_tool"),
        Index("ix_tool_saves_session", "session_id"),
        Index("ix_tool_saves_tool", "tool_id"),
    )
