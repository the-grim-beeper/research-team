from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class ArtifactRead(BaseModel):
    id: int
    subject_id: int
    kind: str
    author_type: Literal["agent", "user"]
    author_id: int | None
    parent_id: int | None
    addressed_to: int | None
    title: str
    body_md: str
    metadata_json: dict[str, Any]
    created_at: datetime
