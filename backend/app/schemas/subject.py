from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SubjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    brief: str = Field(default="", max_length=10_000)


class SubjectRead(BaseModel):
    id: int
    title: str
    brief: str
    status: Literal["active", "archived"]
    created_at: datetime
