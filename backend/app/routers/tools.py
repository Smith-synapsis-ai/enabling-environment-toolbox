"""Tool routers: detail view, rating submission, rating retrieval,
save/unsave, and email capture.

Endpoints:
    GET  /api/tools/{tool_id}          -- full tool detail
    POST /api/tools/{tool_id}/rate     -- submit or update a rating
    GET  /api/tools/{tool_id}/ratings  -- get aggregated rating info
    POST /api/tools/{tool_id}/save     -- save/favorite a tool
    DELETE /api/tools/{tool_id}/save   -- unsave a tool
    POST /api/email-capture            -- capture an email address
"""

import logging
import re
import uuid as _uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.rating import RatingRequest, RatingResponse
from app.schemas.tool import ToolRead
from app.services.tracking import TrackingService

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple email regex for validation
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


# ---------------------------------------------------------------------------
# Schemas for new endpoints
# ---------------------------------------------------------------------------


class EmailCaptureRequest(BaseModel):
    email: str = Field(..., min_length=3, description="Email address")
    session_id: str = Field(..., min_length=1, description="Session identifier")


class EmailCaptureResponse(BaseModel):
    status: str
    email: str
    user_type: str


class SaveResponse(BaseModel):
    status: str
    tool_id: str


# ---------------------------------------------------------------------------
# GET /api/tools/{tool_id}
# ---------------------------------------------------------------------------


@router.get("/tools/{tool_id}", response_model=ToolRead)
async def get_tool(
    tool_id: _uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the full detail of a single tool by its UUID."""
    result = await db.execute(
        text(
            """
            SELECT id, title, summary, what_it_does, when_to_use_it,
                   who_its_for, pillars, domains, type, stage,
                   target_users, geography, authors, date_published,
                   source_url, source_organization, cover_image_url,
                   average_rating, rating_count, view_count,
                   cgspace_id, relevance_score, is_visible,
                   last_verified_at, created_at, updated_at
            FROM tools
            WHERE id = :tool_id
            """
        ),
        {"tool_id": str(tool_id)},
    )
    row = result.mappings().fetchone()

    if row is None or not row["is_visible"]:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Log the view in the background
    session_id = getattr(request.state, "session_id", None)
    referrer = request.query_params.get("ref", "direct")
    background_tasks.add_task(
        TrackingService.log_tool_view,
        tool_id=tool_id,
        session_id=session_id,
        referrer=referrer,
    )

    return ToolRead(
        id=row["id"],
        title=row["title"],
        summary=row["summary"],
        what_it_does=row["what_it_does"],
        when_to_use_it=row["when_to_use_it"],
        who_its_for=row["who_its_for"],
        pillars=row["pillars"],
        domains=row["domains"],
        type=row["type"],
        stage=row["stage"],
        target_users=row["target_users"],
        geography=row["geography"],
        authors=row["authors"],
        date_published=row["date_published"],
        source_url=row["source_url"],
        source_organization=row["source_organization"],
        cover_image_url=row["cover_image_url"],
        average_rating=float(row["average_rating"] or 0),
        rating_count=int(row["rating_count"] or 0),
        view_count=int(row["view_count"] or 0),
        cgspace_id=row["cgspace_id"],
        relevance_score=float(row["relevance_score"]) if row["relevance_score"] is not None else None,
        is_visible=row["is_visible"],
        last_verified_at=row["last_verified_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ---------------------------------------------------------------------------
# POST /api/tools/{tool_id}/rate
# ---------------------------------------------------------------------------


@router.post("/tools/{tool_id}/rate", response_model=RatingResponse)
async def rate_tool(
    tool_id: _uuid.UUID,
    body: RatingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Submit or update a rating for a tool.

    Uses an upsert: if the user has already rated this tool, their
    rating is updated.  After the upsert the tool's aggregate rating
    fields are recalculated.

    Also inserts an immutable record into rating_events for analytics.
    """
    # Verify the tool exists and is visible
    tool_check = await db.execute(
        text("SELECT id FROM tools WHERE id = :tool_id AND is_visible = true"),
        {"tool_id": str(tool_id)},
    )
    if tool_check.fetchone() is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Upsert the rating
    await db.execute(
        text(
            """
            INSERT INTO user_ratings (tool_id, user_identifier, rating)
            VALUES (:tool_id, :user_identifier, :rating)
            ON CONFLICT (tool_id, user_identifier)
            DO UPDATE SET rating = :rating, updated_at = now()
            """
        ),
        {
            "tool_id": str(tool_id),
            "user_identifier": body.user_id,
            "rating": body.rating,
        },
    )

    # Insert immutable rating event log
    session_id = getattr(request.state, "session_id", None)
    await db.execute(
        text(
            """
            INSERT INTO rating_events (tool_id, session_id, user_identifier, rating)
            VALUES (:tool_id, :session_id, :user_identifier, :rating)
            """
        ),
        {
            "tool_id": str(tool_id),
            "session_id": session_id,
            "user_identifier": body.user_id,
            "rating": body.rating,
        },
    )

    # Recalculate aggregate rating on the tool
    await db.execute(
        text(
            """
            UPDATE tools
            SET average_rating = (
                    SELECT COALESCE(AVG(rating), 0)
                    FROM user_ratings WHERE tool_id = :tool_id
                ),
                rating_count = (
                    SELECT COUNT(*)
                    FROM user_ratings WHERE tool_id = :tool_id
                ),
                updated_at = now()
            WHERE id = :tool_id
            """
        ),
        {"tool_id": str(tool_id)},
    )

    await db.commit()

    # Return the updated rating information
    return await _get_rating_response(db, tool_id)


# ---------------------------------------------------------------------------
# GET /api/tools/{tool_id}/ratings
# ---------------------------------------------------------------------------


@router.get("/tools/{tool_id}/ratings", response_model=RatingResponse)
async def get_tool_ratings(
    tool_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated rating statistics for a tool."""
    # Verify the tool exists
    tool_check = await db.execute(
        text("SELECT id FROM tools WHERE id = :tool_id"),
        {"tool_id": str(tool_id)},
    )
    if tool_check.fetchone() is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    return await _get_rating_response(db, tool_id)


# ---------------------------------------------------------------------------
# POST /api/tools/{tool_id}/save
# ---------------------------------------------------------------------------


@router.post("/tools/{tool_id}/save", response_model=SaveResponse)
async def save_tool(
    tool_id: _uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Save/favorite a tool for the current session."""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header is required")

    # Verify tool exists
    tool_check = await db.execute(
        text("SELECT id FROM tools WHERE id = :tool_id"),
        {"tool_id": str(tool_id)},
    )
    if tool_check.fetchone() is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Upsert into tool_saves
    await db.execute(
        text(
            """
            INSERT INTO tool_saves (session_id, tool_id)
            VALUES (:session_id, :tool_id)
            ON CONFLICT (session_id, tool_id) DO NOTHING
            """
        ),
        {
            "session_id": session_id,
            "tool_id": str(tool_id),
        },
    )
    await db.commit()

    return SaveResponse(status="saved", tool_id=str(tool_id))


# ---------------------------------------------------------------------------
# DELETE /api/tools/{tool_id}/save
# ---------------------------------------------------------------------------


@router.delete("/tools/{tool_id}/save", response_model=SaveResponse)
async def unsave_tool(
    tool_id: _uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Remove a saved/favorite tool for the current session."""
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header is required")

    await db.execute(
        text(
            """
            DELETE FROM tool_saves
            WHERE session_id = :session_id AND tool_id = :tool_id
            """
        ),
        {
            "session_id": session_id,
            "tool_id": str(tool_id),
        },
    )
    await db.commit()

    return SaveResponse(status="unsaved", tool_id=str(tool_id))


# ---------------------------------------------------------------------------
# POST /api/email-capture
# ---------------------------------------------------------------------------


@router.post("/email-capture", response_model=EmailCaptureResponse)
async def capture_email(
    body: EmailCaptureRequest,
    db: AsyncSession = Depends(get_db),
):
    """Capture an email address from the modal.

    Upserts into email_captures, updates user_sessions.user_email,
    and auto-classifies user_type based on domain.
    """
    # Validate email format
    if not _EMAIL_RE.match(body.email):
        raise HTTPException(status_code=422, detail="Invalid email format")

    # Determine user type from domain
    email_lower = body.email.lower().strip()
    if email_lower.endswith("@cgiar.org"):
        user_type = "internal"
    else:
        user_type = "external"

    # Upsert into email_captures
    await db.execute(
        text(
            """
            INSERT INTO email_captures (email, session_id, source)
            VALUES (:email, :session_id, 'modal')
            ON CONFLICT (email) DO UPDATE
            SET session_id = COALESCE(EXCLUDED.session_id, email_captures.session_id)
            """
        ),
        {
            "email": email_lower,
            "session_id": body.session_id,
        },
    )

    # Update user_sessions with email and user_type
    await db.execute(
        text(
            """
            UPDATE user_sessions
            SET user_email = :email,
                user_type = :user_type
            WHERE session_id = :session_id
            """
        ),
        {
            "email": email_lower,
            "user_type": user_type,
            "session_id": body.session_id,
        },
    )

    await db.commit()

    return EmailCaptureResponse(
        status="captured",
        email=email_lower,
        user_type=user_type,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _get_rating_response(
    db: AsyncSession, tool_id: _uuid.UUID
) -> RatingResponse:
    """Build a RatingResponse from the database for the given tool."""
    # Aggregate stats
    agg_result = await db.execute(
        text(
            """
            SELECT COALESCE(AVG(rating), 0) AS avg_rating,
                   COUNT(*) AS total_count
            FROM user_ratings
            WHERE tool_id = :tool_id
            """
        ),
        {"tool_id": str(tool_id)},
    )
    agg_row = agg_result.mappings().fetchone()

    # Distribution
    dist_result = await db.execute(
        text(
            """
            SELECT rating, COUNT(*) AS cnt
            FROM user_ratings
            WHERE tool_id = :tool_id
            GROUP BY rating
            ORDER BY rating
            """
        ),
        {"tool_id": str(tool_id)},
    )
    dist_rows = dist_result.mappings().all()

    # Build distribution dict with all 5 levels
    distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for row in dist_rows:
        distribution[str(row["rating"])] = int(row["cnt"])

    return RatingResponse(
        tool_id=tool_id,
        average=round(float(agg_row["avg_rating"]), 2) if agg_row else 0.0,
        count=int(agg_row["total_count"]) if agg_row else 0,
        distribution=distribution,
    )
