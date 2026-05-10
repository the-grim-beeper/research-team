from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class RoleRead(BaseModel):
    id: int
    slug: str
    display_name: str
    category: Literal["admin", "expert"]
    default_system_prompt: str
    default_model: str
    default_cycle: str
    default_tier: Literal["cheap", "mid", "premium"]
    tools: list[Any]
    created_at: datetime


class RoleEmbed(BaseModel):
    id: int
    slug: str
    display_name: str
    category: Literal["admin", "expert"]
