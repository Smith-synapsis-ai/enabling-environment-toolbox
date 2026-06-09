import uuid
from datetime import datetime

from sqlalchemy import (
    Text,
    Integer,
    Boolean,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    prompt_name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("prompt_name", "version", name="uq_prompt_name_version"),
        # Partial unique index: only one active per prompt_name
        Index(
            "ix_prompt_active_unique",
            "prompt_name",
            unique=True,
            postgresql_where=(text_column := "is_active = true"),
        ),
    )


# Fix: the partial unique index needs proper SQLAlchemy text expression
# We'll handle it in the migration instead
PromptVersion.__table_args__ = (
    UniqueConstraint("prompt_name", "version", name="uq_prompt_name_version"),
)


class PromptEvalResult(Base):
    __tablename__ = "prompt_eval_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    prompt_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=False
    )
    input_data = mapped_column(JSONB, nullable=True)
    output_data = mapped_column(JSONB, nullable=True)
    expected_output = mapped_column(JSONB, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    model_used: Mapped[str | None] = mapped_column(Text)
    tokens_input: Mapped[int | None] = mapped_column(Integer)
    tokens_output: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6))
    notes: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime | None] = mapped_column()
    evaluated_by: Mapped[str | None] = mapped_column(Text)  # 'human' or 'automated'
