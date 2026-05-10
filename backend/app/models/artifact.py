from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    author_type: Mapped[str] = mapped_column(String(8), nullable=False)
    author_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("artifacts.id"), index=True, nullable=True
    )
    addressed_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    body_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
