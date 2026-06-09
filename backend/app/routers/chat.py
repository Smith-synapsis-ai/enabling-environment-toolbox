"""Chat router: conversational AI endpoint with tool recommendations.

Endpoint:
    POST /api/chat  -- multi-turn conversation with tool search integration
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import generate_response
from app.services.tracking import TrackingService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the conversational AI advisor.

    On the first request, omit ``conversation_id`` and one will be
    generated.  Include it in subsequent requests to continue the
    conversation.
    """
    session_id = getattr(request.state, "session_id", None)

    try:
        response = await generate_response(
            conversation_id=body.conversation_id,
            user_message=body.message,
            db=db,
            session_id=session_id,
        )
    except Exception:
        logger.exception("Chat generation failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate chat response",
        )
    tool_ids = (
        [t.id for t in response.tools_recommended]
        if response.tools_recommended
        else None
    )
    result_count = len(response.tools_recommended) if response.tools_recommended else 0

    background_tasks.add_task(
        TrackingService.log_search,
        session_id=session_id,
        query=body.message,
        query_type="chat",
        filters=None,
        result_count=result_count,
        result_ids=tool_ids,
    )

    return response
