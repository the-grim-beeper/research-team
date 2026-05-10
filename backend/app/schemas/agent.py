from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.role import RoleEmbed


class AgentRead(BaseModel):
    id: int
    subject_id: int
    role: RoleEmbed
    display_name: str
    system_prompt: str
    model: str
    cycle: str
    daily_budget_usd: Decimal
    spent_today_usd: Decimal
    last_run_at: datetime | None
    created_at: datetime


class AgentUpdate(BaseModel):
    model: str | None = Field(default=None, max_length=128)
    cycle: str | None = None
    daily_budget_usd: Decimal | None = None
    system_prompt_addendum: str | None = Field(default=None, max_length=10_000)
