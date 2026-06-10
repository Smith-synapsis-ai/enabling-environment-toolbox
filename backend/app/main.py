import asyncio
import uuid

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text, func as sa_func, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import get_db, async_engine
from app.models.prompt import PromptVersion
from app.schemas.prompt import PromptVersionCreate, PromptVersionRead

# Import all models so Alembic sees them
from app.models import (  # noqa: F401
    Base, Tool, UserRating, SearchLog, ToolView, UserSession, EmailCapture,
    PromptVersion, PromptEvalResult, ConversationTurn, RatingEvent,
    AdminToken, ToolSave, PulseSurveyResponse,
)

# Import routers
from app.routers import search, chat, tools, metrics, admin, admin_analytics, pulse_survey
from app.routers import assistant

# Import services
from app.services.tracking import TrackingService

app = FastAPI(
    title="Enabling Environment Toolbox API",
    version="0.3.0",
    description="CGIAR Enabling Environment Toolbox -- Phase 2 API",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# CORS origins: configurable via settings, defaults to permissive for local dev
_cors_origins = (
    ["*"] if settings.CORS_ORIGINS == "*"
    else [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
)

# Also allow AWS Amplify default domains (https://*.amplifyapp.com) so that
# deployments work before custom domains are configured in each environment.
_cors_origin_regex = (
    None if settings.CORS_ORIGINS == "*"
    else r"https://.*\.amplifyapp\.com"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SessionMiddleware(BaseHTTPMiddleware):
    """Extract the X-Session-ID header, attach it to request.state,
    and fire a background task to ensure the session is tracked in the DB.

    Also captures UTM parameters from query string on first request.
    """

    async def dispatch(self, request: Request, call_next):
        session_id = request.headers.get("X-Session-ID")
        request.state.session_id = session_id

        if session_id:
            user_agent = request.headers.get("User-Agent")
            ip_address = request.client.host if request.client else None

            # Fire session tracking as a background task (non-blocking)
            asyncio.create_task(
                TrackingService.ensure_session(
                    session_id=session_id,
                    user_agent=user_agent,
                    ip_address=ip_address,
                )
            )

        response = await call_next(request)
        return response


app.add_middleware(SessionMiddleware)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(tools.router, prefix="/api", tags=["Tools"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(admin_analytics.router, prefix="/api", tags=["Admin Analytics"])
app.include_router(pulse_survey.router, prefix="/api", tags=["Pulse Survey"])
app.include_router(assistant.router, tags=["Assistant"])  # carries own /api + /ws paths

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health")
async def health_check():
    """Health check endpoint — verifies the SQLite agent store is accessible.

    On EC2 the session DB is SQLite (replicated via Litestream to S3).
    The legacy async_engine (Postgres) is not used on EC2; checking it would
    always return an error because no Postgres runs there.
    """
    import os
    import sqlite3 as _sqlite3

    db_path = os.environ.get("AGENT_STORE_PATH", "/app/backend/data/agent_store.db")
    try:
        if os.path.exists(db_path):
            with _sqlite3.connect(db_path, check_same_thread=False) as conn:
                conn.execute("SELECT 1")
            return {"status": "ok", "database": "connected"}
        else:
            # DB not yet restored from Litestream (first boot or cold start)
            return {"status": "ok", "database": "initializing"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


# ---------- Prompt Store Endpoints ----------


@app.get("/api/prompts", response_model=list[PromptVersionRead])
async def list_prompts(db: AsyncSession = Depends(get_db)):
    """List all prompt versions, ordered by name then version descending."""
    result = await db.execute(
        select(PromptVersion).order_by(
            PromptVersion.prompt_name,
            PromptVersion.version.desc(),
        )
    )
    return result.scalars().all()


@app.get("/api/prompts/{name}/active", response_model=PromptVersionRead)
async def get_active_prompt(name: str, db: AsyncSession = Depends(get_db)):
    """Get the currently active prompt version for a given prompt name."""
    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.prompt_name == name,
            PromptVersion.is_active == True,  # noqa: E712
        )
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active prompt found for name '{name}'",
        )
    return prompt


@app.post("/api/prompts", response_model=PromptVersionRead, status_code=201)
async def create_prompt_version(
    payload: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new prompt version. Auto-increments the version number."""
    # Get the next version number for this prompt_name
    result = await db.execute(
        select(sa_func.coalesce(sa_func.max(PromptVersion.version), 0)).where(
            PromptVersion.prompt_name == payload.prompt_name
        )
    )
    max_version = result.scalar()
    next_version = max_version + 1

    new_prompt = PromptVersion(
        prompt_name=payload.prompt_name,
        version=next_version,
        prompt_text=payload.prompt_text,
        model=payload.model,
        notes=payload.notes,
        created_by=payload.created_by,
        is_active=False,
    )
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)
    return new_prompt


@app.put("/api/prompts/{prompt_id}/activate", response_model=PromptVersionRead)
async def activate_prompt_version(
    prompt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Activate a prompt version. Deactivates all other versions with the same prompt_name."""
    # Fetch the target prompt
    result = await db.execute(
        select(PromptVersion).where(PromptVersion.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    # Deactivate all other versions of the same prompt_name
    await db.execute(
        update(PromptVersion)
        .where(
            PromptVersion.prompt_name == prompt.prompt_name,
            PromptVersion.id != prompt_id,
        )
        .values(is_active=False)
    )

    # Activate the target
    prompt.is_active = True
    await db.commit()
    await db.refresh(prompt)
    return prompt
