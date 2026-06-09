"""Pulse survey endpoint for collecting user feedback."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class PulseSurveyRequest(BaseModel):
    session_id: str
    question_key: str = Field(..., pattern="^(trust_recommendations|helped_decide)$")
    score: int = Field(..., ge=1, le=5)


class PulseSurveyResponseSchema(BaseModel):
    message: str


@router.post("/pulse-survey", response_model=PulseSurveyResponseSchema, status_code=201)
async def submit_pulse_survey(
    body: PulseSurveyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a pulse survey response."""
    await db.execute(
        text("""
            INSERT INTO pulse_survey_responses (session_id, question_key, score)
            VALUES (:session_id, :question_key, :score)
        """),
        {
            "session_id": body.session_id,
            "question_key": body.question_key,
            "score": body.score,
        },
    )
    await db.commit()
    logger.info(
        "Pulse survey response: session=%s, question=%s, score=%d",
        body.session_id,
        body.question_key,
        body.score,
    )
    return PulseSurveyResponseSchema(message="Survey response recorded")
