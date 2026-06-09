"""PulseSurveyResponse model — immutable log of user pulse survey answers."""

import uuid
from datetime import datetime

from sqlalchemy import Text, Integer, Index, func, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class PulseSurveyResponse(Base):
    __tablename__ = "pulse_survey_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    question_key: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 5", name="ck_pulse_survey_score_range"),
        Index("ix_pulse_survey_session", "session_id"),
        Index("ix_pulse_survey_question", "question_key"),
    )
