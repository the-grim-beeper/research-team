from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CorpusItemRead(BaseModel):
    id: int
    subject_id: int
    source_id: int | None
    external_id: str | None
    title: str
    authors_json: list[Any]
    published_at: datetime | None
    url: str | None
    summary: str | None
    tags_json: list[Any]
    importance: int | None
    created_at: datetime
