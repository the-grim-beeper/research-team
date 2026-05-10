from datetime import datetime
from typing import Any

from pydantic import BaseModel


class BibliographyEntryRead(BaseModel):
    id: int
    subject_id: int
    corpus_item_id: int
    comments: str
    created_at: datetime
    updated_at: datetime
    title: str
    url: str | None
    authors: list[Any]
    summary: str | None
    tags: list[Any]
    importance: int | None


class CommentAppend(BaseModel):
    comment: str


class TextNote(BaseModel):
    title: str = ""
    text: str


class UrlIngest(BaseModel):
    url: str
