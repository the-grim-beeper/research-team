from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bibliography import BibliographyEntry
from app.models.corpus import CorpusItem


async def upsert(
    session: AsyncSession,
    *,
    subject_id: int,
    corpus_item_id: int,
    initial_comment: str,
) -> BibliographyEntry:
    existing = await session.scalar(
        select(BibliographyEntry).where(BibliographyEntry.corpus_item_id == corpus_item_id)
    )
    now = datetime.now(timezone.utc)
    if existing:
        return existing
    entry = BibliographyEntry(
        subject_id=subject_id,
        corpus_item_id=corpus_item_id,
        comments=initial_comment,
        created_at=now,
        updated_at=now,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def append_comment(
    session: AsyncSession, entry_id: int, comment: str
) -> BibliographyEntry:
    entry = await session.get(BibliographyEntry, entry_id)
    if entry is None:
        raise LookupError(f"BibliographyEntry {entry_id} not found")
    if entry.comments:
        entry.comments = entry.comments.rstrip() + "\n\n" + comment.strip()
    else:
        entry.comments = comment.strip()
    entry.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(entry)
    return entry


async def list_for_subject(
    session: AsyncSession, subject_id: int
) -> list[tuple[BibliographyEntry, CorpusItem]]:
    rows = await session.execute(
        select(BibliographyEntry, CorpusItem)
        .join(CorpusItem, CorpusItem.id == BibliographyEntry.corpus_item_id)
        .where(BibliographyEntry.subject_id == subject_id)
        .order_by(BibliographyEntry.updated_at.desc())
    )
    return [(r[0], r[1]) for r in rows.all()]
