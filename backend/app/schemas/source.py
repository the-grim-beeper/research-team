from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class SourceCreate(BaseModel):
    kind: Literal["rss", "arxiv", "url", "notes"]
    display_name: str = ""
    config: dict[str, Any] = {}


class SourceRead(BaseModel):
    id: int
    subject_id: int
    kind: str
    display_name: str
    config_json: dict[str, Any]
    created_at: datetime
