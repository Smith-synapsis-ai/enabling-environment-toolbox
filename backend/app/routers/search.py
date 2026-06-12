"""Search routers: semantic (vector) and catalog (faceted) search.

Endpoints:
    POST /api/search/semantic  -- pgvector cosine similarity search
    POST /api/search/catalog   -- faceted filter + keyword search with facet counts
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

import traceback

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.search import (
    CatalogSearchRequest,
    CatalogSearchResponse,
    FacetCounts,
    SemanticSearchRequest,
    SemanticSearchResponse,
    ToolSearchResult,
)
from app.services.tracking import TrackingService

logger = logging.getLogger(__name__)

router = APIRouter()

# Ensure the pipeline package is importable (it lives outside the backend package)
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ---------------------------------------------------------------------------
# POST /api/search/semantic
# ---------------------------------------------------------------------------


@router.post("/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    body: SemanticSearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Perform a vector-similarity search over all visible tools."""
    try:
        from pipeline.embeddings import generate_embedding
    except ImportError as exc:
        logger.error("Cannot import pipeline.embeddings: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Embedding pipeline is not available",
        )

    # Generate the query embedding (sync function -> offload to thread)
    try:
        query_vector = await asyncio.to_thread(generate_embedding, body.query)
    except Exception as exc:
        logger.exception("Embedding generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate query embedding")

    # Format for pgvector
    vector_literal = "[" + ",".join(str(v) for v in query_vector) + "]"

    # Execute the pgvector cosine similarity query
    result = await db.execute(
        text(
            """
            SELECT id, title, summary, what_it_does, when_to_use_it,
                   who_its_for, pillars, domains, type, stage,
                   target_users, geography, source_url, cover_image_url,
                   average_rating, rating_count,
                   1 - (embedding <=> CAST(:vec AS vector)) AS similarity
            FROM tools
            WHERE embedding IS NOT NULL AND is_visible = true
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :limit
            """
        ),
        {"vec": vector_literal, "limit": body.top_n},
    )
    rows = result.mappings().all()

    # Build result list, filtering by min_similarity
    results: list[ToolSearchResult] = []
    for row in rows:
        sim = float(row["similarity"]) if row["similarity"] is not None else 0.0
        if sim < body.min_similarity:
            continue
        results.append(
            ToolSearchResult(
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
                source_url=row["source_url"],
                cover_image_url=row["cover_image_url"],
                average_rating=float(row["average_rating"] or 0),
                rating_count=int(row["rating_count"] or 0),
                similarity=round(sim, 4),
            )
        )

    # Log the search in the background
    session_id = getattr(request.state, "session_id", None)
    result_ids = [r.id for r in results]
    background_tasks.add_task(
        TrackingService.log_search,
        session_id=session_id,
        query=body.query,
        query_type="semantic",
        filters=None,
        result_count=len(results),
        result_ids=result_ids,
    )

    return SemanticSearchResponse(
        query=body.query,
        total_results=len(results),
        results=results,
    )


# ---------------------------------------------------------------------------
# POST /api/search/catalog
# ---------------------------------------------------------------------------


@router.post("/search/catalog", response_model=CatalogSearchResponse)
async def catalog_search(
    body: CatalogSearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Perform a faceted catalog search with optional keyword matching."""
    try:
        return await _catalog_search_impl(body, request, background_tasks, db)
    except Exception as exc:
        tb = traceback.format_exc()
        logger.error("catalog_search UNHANDLED: %s\n%s", exc, tb)
        return JSONResponse(
            status_code=500,
            content={"error": type(exc).__name__, "detail": str(exc), "traceback": tb},
        )


async def _catalog_search_impl(
    body: CatalogSearchRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> CatalogSearchResponse:
    """Inner implementation — wrapped by catalog_search for debug error reporting."""
    # Build the dynamic WHERE clause
    conditions: list[str] = ["is_visible = true"]
    params: dict = {}

    if body.pillars:
        conditions.append("pillars && CAST(:pillars AS text[])")
        params["pillars"] = body.pillars

    if body.domains:
        conditions.append("domains && CAST(:domains AS text[])")
        params["domains"] = body.domains

    if body.type:
        conditions.append("type = :type")
        params["type"] = body.type

    if body.stage:
        conditions.append("stage = :stage")
        params["stage"] = body.stage

    if body.target_users:
        conditions.append("target_users && CAST(:target_users AS text[])")
        params["target_users"] = body.target_users

    if body.geography:
        conditions.append("geography && CAST(:geography AS text[])")
        params["geography"] = body.geography

    if body.keyword:
        conditions.append(
            "to_tsvector('english', coalesce(title,'') || ' ' || coalesce(summary,'')) "
            "@@ plainto_tsquery('english', :keyword)"
        )
        params["keyword"] = body.keyword

    where_clause = " AND ".join(conditions)

    # ---- Total count ----
    count_sql = f"SELECT COUNT(*) FROM tools WHERE {where_clause}"
    count_result = await db.execute(text(count_sql), params)
    total = count_result.scalar() or 0

    # ---- Sorting ----
    if body.sort_by == "date":
        order_clause = "date_published DESC NULLS LAST"
    elif body.sort_by == "rating":
        order_clause = "average_rating DESC, rating_count DESC"
    else:
        # relevance: if keyword present use ts_rank, otherwise alphabetical
        if body.keyword:
            order_clause = (
                "ts_rank(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(summary,'')), "
                "plainto_tsquery('english', :keyword)) DESC"
            )
        else:
            order_clause = "title ASC"

    # ---- Paginated results ----
    offset = (body.page - 1) * body.page_size
    results_sql = f"""
        SELECT id, title, summary, what_it_does, when_to_use_it,
               who_its_for, pillars, domains, type, stage,
               target_users, geography, source_url, cover_image_url,
               average_rating, rating_count
        FROM tools
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT :page_size OFFSET :offset
    """
    params_with_pagination = {**params, "page_size": body.page_size, "offset": offset}

    result = await db.execute(text(results_sql), params_with_pagination)
    rows = result.mappings().all()

    results: list[ToolSearchResult] = []
    for row in rows:
        results.append(
            ToolSearchResult(
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
                source_url=row["source_url"],
                cover_image_url=row["cover_image_url"],
                average_rating=float(row["average_rating"] or 0),
                rating_count=int(row["rating_count"] or 0),
                similarity=0.0,  # Not applicable for catalog search
            )
        )

    # ---- Facet counts ----
    # For each taxonomy dimension, count with ALL OTHER filters applied
    # but NOT the filter for that dimension.
    facets = await _compute_facets(db, body, conditions, params)

    # Log the search in the background
    session_id = getattr(request.state, "session_id", None)
    filters_used = {}
    if body.pillars:
        filters_used["pillars"] = body.pillars
    if body.domains:
        filters_used["domains"] = body.domains
    if body.type:
        filters_used["type"] = body.type
    if body.stage:
        filters_used["stage"] = body.stage
    if body.target_users:
        filters_used["target_users"] = body.target_users
    if body.geography:
        filters_used["geography"] = body.geography
    if body.keyword:
        filters_used["keyword"] = body.keyword

    result_ids = [r.id for r in results]
    background_tasks.add_task(
        TrackingService.log_search,
        session_id=session_id,
        query=body.keyword or "",
        query_type="faceted",
        filters=filters_used or None,
        result_count=total,
        result_ids=result_ids,
    )

    return CatalogSearchResponse(
        total=total,
        page=body.page,
        page_size=body.page_size,
        results=results,
        facets=facets,
    )


# ---------------------------------------------------------------------------
# Facet computation helpers
# ---------------------------------------------------------------------------

# Maps each facet dimension to:
#   (request_field, sql_condition_prefix, is_array)
_FACET_DIMENSIONS = {
    "pillars": ("pillars", "pillars && CAST(:pillars AS text[])", True),
    "domains": ("domains", "domains && CAST(:domains AS text[])", True),
    "type": ("type", "type = :type", False),
    "stage": ("stage", "stage = :stage", False),
    "target_users": ("target_users", "target_users && CAST(:target_users AS text[])", True),
    "geography": ("geography", "geography && CAST(:geography AS text[])", True),
}


async def _compute_facets(
    db: AsyncSession,
    body: CatalogSearchRequest,
    all_conditions: list[str],
    all_params: dict,
) -> FacetCounts:
    """Compute facet counts for each taxonomy dimension.

    For each dimension, we run a count query with all filters EXCEPT the
    filter for that dimension.  This gives the user accurate counts of
    what they *could* see if they changed just one filter.
    """
    facet_data: dict[str, dict[str, int]] = {}

    for dim_name, (field_name, condition_str, is_array) in _FACET_DIMENSIONS.items():
        # Build conditions excluding the filter for *this* dimension
        other_conditions = ["is_visible = true"]
        other_params: dict = {}

        # Keyword is always applied across all facets
        if body.keyword:
            other_conditions.append(
                "to_tsvector('english', coalesce(title,'') || ' ' || coalesce(summary,'')) "
                "@@ plainto_tsquery('english', :keyword)"
            )
            other_params["keyword"] = body.keyword

        # Add all filters except the current dimension
        for other_dim, (other_field, other_cond, other_is_array) in _FACET_DIMENSIONS.items():
            if other_dim == dim_name:
                continue  # Skip the current dimension
            filter_val = getattr(body, other_field)
            if filter_val is not None and (not isinstance(filter_val, list) or len(filter_val) > 0):
                other_conditions.append(other_cond)
                other_params[other_field] = filter_val

        other_where = " AND ".join(other_conditions)

        if is_array:
            # For array columns, unnest and count each distinct value.
            # COALESCE guards against NULL array columns (unnest(NULL) errors in
            # PostgreSQL's implicit cross-join form).
            facet_sql = f"""
                SELECT val, COUNT(*) AS cnt
                FROM tools, unnest(COALESCE({dim_name}, ARRAY[]::text[])) AS val
                WHERE {other_where}
                GROUP BY val
                ORDER BY cnt DESC
            """
        else:
            # For scalar columns, just group by the column
            facet_sql = f"""
                SELECT {dim_name} AS val, COUNT(*) AS cnt
                FROM tools
                WHERE {other_where} AND {dim_name} IS NOT NULL
                GROUP BY {dim_name}
                ORDER BY cnt DESC
            """

        result = await db.execute(text(facet_sql), other_params)
        rows = result.mappings().all()
        facet_data[dim_name] = {row["val"]: int(row["cnt"]) for row in rows}

    return FacetCounts(**facet_data)
