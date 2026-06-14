"""Pydantic schemas for semantic and catalog search endpoints."""

import uuid
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


class SemanticSearchRequest(BaseModel):
    """Request body for POST /api/search/semantic."""

    query: str = Field(..., min_length=1, description="Natural-language search query")
    top_n: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    min_similarity: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum cosine similarity threshold"
    )


class ToolSearchResult(BaseModel):
    """A single tool result with similarity score."""

    id: uuid.UUID
    cgspace_id: str | None = None
    title: str
    summary: str | None = None
    what_it_does: str | None = None
    when_to_use_it: str | None = None
    who_its_for: str | None = None
    pillars: list[str] | None = None
    domains: list[str] | None = None
    type: str | None = None
    stage: str | None = None
    target_users: list[str] | None = None
    geography: list[str] | None = None
    source_url: str | None = None
    cover_image_url: str | None = None
    average_rating: float = 0.0
    rating_count: int = 0
    similarity: float = 0.0

    model_config = {"from_attributes": True}


class SemanticSearchResponse(BaseModel):
    """Response for semantic search."""

    query: str
    total_results: int
    results: list[ToolSearchResult]


# ---------------------------------------------------------------------------
# Catalog / faceted search
# ---------------------------------------------------------------------------


class CatalogSearchRequest(BaseModel):
    """Request body for POST /api/search/catalog."""

    pillars: Optional[list[str]] = None
    domains: Optional[list[str]] = None
    type: Optional[str] = None
    stage: Optional[str] = None
    target_users: Optional[list[str]] = None
    geography: Optional[list[str]] = None
    keyword: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: Literal["relevance", "date", "rating"] = "relevance"


class FacetCounts(BaseModel):
    """Facet count distributions for each taxonomy dimension."""

    pillars: dict[str, int] = {}
    domains: dict[str, int] = {}
    type: dict[str, int] = {}
    stage: dict[str, int] = {}
    target_users: dict[str, int] = {}
    geography: dict[str, int] = {}


class CatalogSearchResponse(BaseModel):
    """Response for catalog/faceted search."""

    total: int
    page: int
    page_size: int
    results: list[ToolSearchResult]
    facets: FacetCounts
