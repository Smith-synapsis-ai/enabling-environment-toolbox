"""Admin routers: authentication and tool management (CRUD).

Endpoints:
    POST /api/admin/login              -- authenticate and get bearer token
    GET  /api/admin/tools              -- list all tools (including hidden)
    POST /api/admin/tools              -- create a new tool
    PUT  /api/admin/tools/{tool_id}    -- update a tool
    DELETE /api/admin/tools/{tool_id}  -- delete a tool
"""

import logging
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, AsyncSessionLocal
from app.schemas.tool import ToolCreate, ToolRead, ToolUpdate

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Token expiration duration
# ---------------------------------------------------------------------------

TOKEN_EXPIRY_HOURS = 24


# ---------------------------------------------------------------------------
# Request/Response schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str


class DeleteResponse(BaseModel):
    message: str


class AdminToolsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    tools: list[ToolRead]


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------


async def verify_admin_token(
    authorization: str = Header(..., description="Bearer token"),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Dependency that validates the Authorization header against the admin_tokens table."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token_str = authorization[len("Bearer "):]

    try:
        token_uuid = _uuid.UUID(token_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(
        text(
            """
            SELECT username, expires_at
            FROM admin_tokens
            WHERE token = :token
            """
        ),
        {"token": str(token_uuid)},
    )
    row = result.mappings().fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Check expiration
    expires_at = row["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        # Clean up expired token
        await db.execute(
            text("DELETE FROM admin_tokens WHERE token = :token"),
            {"token": str(token_uuid)},
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return row["username"]


# ---------------------------------------------------------------------------
# POST /api/admin/login
# ---------------------------------------------------------------------------


@router.post("/admin/login", response_model=LoginResponse)
async def admin_login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with credentials and return a bearer token stored in the DB."""
    if body.username != settings.ADMIN_USERNAME or body.password != settings.ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Delete expired tokens for this username
    await db.execute(
        text(
            """
            DELETE FROM admin_tokens
            WHERE username = :username AND expires_at < now()
            """
        ),
        {"username": body.username},
    )

    # Create new token
    token = _uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)

    await db.execute(
        text(
            """
            INSERT INTO admin_tokens (token, username, expires_at)
            VALUES (:token, :username, :expires_at)
            """
        ),
        {
            "token": str(token),
            "username": body.username,
            "expires_at": expires_at,
        },
    )
    await db.commit()

    return LoginResponse(token=str(token))


# ---------------------------------------------------------------------------
# GET /api/admin/tools
# ---------------------------------------------------------------------------


@router.get("/admin/tools", response_model=AdminToolsResponse)
async def list_admin_tools(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    keyword: str | None = Query(None),
    sort_by: str = Query("title"),
    _user: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """List all tools including hidden ones, with pagination, search, and sorting."""
    # Build WHERE clause
    where_clauses: list[str] = []
    params: dict = {}

    if keyword:
        where_clauses.append(
            "(LOWER(title) LIKE :keyword OR LOWER(summary) LIKE :keyword)"
        )
        params["keyword"] = f"%{keyword.lower()}%"

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    # Sort mapping
    sort_map = {
        "title": "title ASC",
        "date": "date_published DESC NULLS LAST",
        "type": "type ASC NULLS LAST",
    }
    order_sql = sort_map.get(sort_by, "title ASC")

    # Count total
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM tools {where_sql}"),
        params,
    )
    total = count_result.scalar()

    # Fetch page
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(
        text(
            f"""
            SELECT id, title, summary, what_it_does, when_to_use_it,
                   who_its_for, pillars, domains, type, stage,
                   target_users, geography, authors, date_published,
                   source_url, source_organization, cover_image_url,
                   average_rating, rating_count, view_count,
                   cgspace_id, relevance_score, is_visible,
                   created_at, updated_at
            FROM tools
            {where_sql}
            ORDER BY {order_sql}
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    rows = result.mappings().all()

    tools = [
        ToolRead(
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
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]

    return AdminToolsResponse(
        total=total,
        page=page,
        page_size=page_size,
        tools=tools,
    )


# ---------------------------------------------------------------------------
# POST /api/admin/tools
# ---------------------------------------------------------------------------


@router.post("/admin/tools", response_model=ToolRead, status_code=201)
async def create_tool(
    body: ToolCreate,
    _user: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Create a new tool."""
    tool_id = _uuid.uuid4()

    await db.execute(
        text(
            """
            INSERT INTO tools (
                id, title, summary, what_it_does, when_to_use_it,
                who_its_for, pillars, domains, type, stage,
                target_users, geography, authors, date_published,
                source_url, source_organization, cover_image_url,
                cgspace_id, relevance_score, is_visible
            ) VALUES (
                :id, :title, :summary, :what_it_does, :when_to_use_it,
                :who_its_for, :pillars, :domains, :type, :stage,
                :target_users, :geography, :authors, :date_published,
                :source_url, :source_organization, :cover_image_url,
                :cgspace_id, :relevance_score, :is_visible
            )
            """
        ),
        {
            "id": str(tool_id),
            "title": body.title,
            "summary": body.summary,
            "what_it_does": body.what_it_does,
            "when_to_use_it": body.when_to_use_it,
            "who_its_for": body.who_its_for,
            "pillars": body.pillars,
            "domains": body.domains,
            "type": body.type,
            "stage": body.stage,
            "target_users": body.target_users,
            "geography": body.geography,
            "authors": body.authors,
            "date_published": body.date_published,
            "source_url": body.source_url,
            "source_organization": body.source_organization,
            "cover_image_url": body.cover_image_url,
            "cgspace_id": body.cgspace_id,
            "relevance_score": body.relevance_score,
            "is_visible": body.is_visible,
        },
    )
    await db.commit()

    # Fetch the created tool to return it with server-generated fields
    result = await db.execute(
        text(
            """
            SELECT id, title, summary, what_it_does, when_to_use_it,
                   who_its_for, pillars, domains, type, stage,
                   target_users, geography, authors, date_published,
                   source_url, source_organization, cover_image_url,
                   average_rating, rating_count, view_count,
                   cgspace_id, relevance_score, is_visible,
                   created_at, updated_at
            FROM tools
            WHERE id = :tool_id
            """
        ),
        {"tool_id": str(tool_id)},
    )
    row = result.mappings().fetchone()

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
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ---------------------------------------------------------------------------
# PUT /api/admin/tools/{tool_id}
# ---------------------------------------------------------------------------


@router.put("/admin/tools/{tool_id}", response_model=ToolRead)
async def update_tool(
    tool_id: _uuid.UUID,
    body: ToolUpdate,
    _user: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Update a tool. Only provided fields are updated."""
    # Verify the tool exists
    check = await db.execute(
        text("SELECT id FROM tools WHERE id = :tool_id"),
        {"tool_id": str(tool_id)},
    )
    if check.fetchone() is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Build dynamic SET clause from provided fields
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Always update updated_at
    set_clauses = [f"{field} = :{field}" for field in update_data]
    set_clauses.append("updated_at = now()")
    set_sql = ", ".join(set_clauses)

    params = {field: value for field, value in update_data.items()}
    params["tool_id"] = str(tool_id)

    await db.execute(
        text(f"UPDATE tools SET {set_sql} WHERE id = :tool_id"),
        params,
    )
    await db.commit()

    # Fetch and return the updated tool
    result = await db.execute(
        text(
            """
            SELECT id, title, summary, what_it_does, when_to_use_it,
                   who_its_for, pillars, domains, type, stage,
                   target_users, geography, authors, date_published,
                   source_url, source_organization, cover_image_url,
                   average_rating, rating_count, view_count,
                   cgspace_id, relevance_score, is_visible,
                   created_at, updated_at
            FROM tools
            WHERE id = :tool_id
            """
        ),
        {"tool_id": str(tool_id)},
    )
    row = result.mappings().fetchone()

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
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# ---------------------------------------------------------------------------
# DELETE /api/admin/tools/{tool_id}
# ---------------------------------------------------------------------------


@router.delete("/admin/tools/{tool_id}", response_model=DeleteResponse)
async def delete_tool(
    tool_id: _uuid.UUID,
    _user: str = Depends(verify_admin_token),
    db: AsyncSession = Depends(get_db),
):
    """Delete a tool and its related records (hard delete)."""
    # Verify the tool exists
    check = await db.execute(
        text("SELECT id FROM tools WHERE id = :tool_id"),
        {"tool_id": str(tool_id)},
    )
    if check.fetchone() is None:
        raise HTTPException(status_code=404, detail="Tool not found")

    # Delete related ratings first
    await db.execute(
        text("DELETE FROM user_ratings WHERE tool_id = :tool_id"),
        {"tool_id": str(tool_id)},
    )

    # Delete the tool
    await db.execute(
        text("DELETE FROM tools WHERE id = :tool_id"),
        {"tool_id": str(tool_id)},
    )

    await db.commit()

    return DeleteResponse(message="Tool deleted")
