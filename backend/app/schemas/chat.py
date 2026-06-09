"""Pydantic schemas for the conversational chat endpoint."""

import uuid
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    message: str = Field(..., min_length=1, description="User message")
    conversation_id: Optional[str] = Field(
        default=None,
        description="Existing conversation ID to continue, or None to start a new one",
    )


class ToolRecommendation(BaseModel):
    """A tool recommended by the chat assistant, with a tailored explanation."""

    id: uuid.UUID
    title: str
    explanation: str
    similarity: float


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    conversation_id: str
    message: str
    tools_recommended: list[ToolRecommendation] | None = None
    conversation_complete: bool = False
