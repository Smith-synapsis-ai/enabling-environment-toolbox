import uuid
from datetime import datetime
from pydantic import BaseModel


class PromptVersionBase(BaseModel):
    prompt_name: str
    prompt_text: str
    model: str | None = None
    notes: str | None = None
    created_by: str | None = None


class PromptVersionCreate(PromptVersionBase):
    pass


class PromptVersionRead(PromptVersionBase):
    id: uuid.UUID
    version: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptVersionActivate(BaseModel):
    id: uuid.UUID
    prompt_name: str
    version: int
    is_active: bool

    model_config = {"from_attributes": True}
