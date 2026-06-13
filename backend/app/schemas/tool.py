import uuid
from datetime import date, datetime
from pydantic import BaseModel


class ToolBase(BaseModel):
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
    authors: list[str] | None = None
    date_published: date | None = None
    source_url: str | None = None
    source_organization: str | None = None
    cover_image_url: str | None = None
    cgspace_id: str | None = None
    relevance_score: float | None = None
    is_visible: bool = True


class ToolCreate(ToolBase):
    pass


class ToolUpdate(BaseModel):
    title: str | None = None
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
    authors: list[str] | None = None
    date_published: date | None = None
    source_url: str | None = None
    source_organization: str | None = None
    cover_image_url: str | None = None
    cgspace_id: str | None = None
    relevance_score: float | None = None
    is_visible: bool | None = None


class ToolRead(ToolBase):
    id: uuid.UUID
    average_rating: float
    rating_count: int
    view_count: int
    last_verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
