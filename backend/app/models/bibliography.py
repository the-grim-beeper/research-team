from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class BibliographyEntry(Base):
    __tablename__ = "bibliography_entries"
    __table_args__ = (UniqueConstraint("corpus_item_id", name="uq_bibliography_corpus_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    corpus_item_id: Mapped[int] = mapped_column(
        ForeignKey("corpus_items.id", ondelete="CASCADE"), nullable=False
    )
    comments: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
