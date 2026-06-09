"""ConversationTurn model — persists chat conversation turns to the database."""

import uuid
from datetime import datetime

from sqlalchemy import Text, Integer, CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    conversation_id: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str | None] = mapped_column(Text)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_tool_ids = mapped_column(
        ARRAY(UUID(as_uuid=True)), server_default="{}", nullable=True
    )
    search_query: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_conversation_turns_role"),
        Index("ix_conversation_turns_conv_id", "conversation_id"),
        Index("ix_conversation_turns_session", "session_id"),
    )
