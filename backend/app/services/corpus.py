from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corpus import CorpusItem


async def list_for_subject(
    session: AsyncSession, subject_id: int, limit: int = 100
) -> list[CorpusItem]:
    rows = await session.scalars(
        select(CorpusItem)
        .where(CorpusItem.subject_id == subject_id)
        .order_by(CorpusItem.created_at.desc())
        .limit(limit)
    )
    return list(rows.all())


async def list_unprocessed(
    session: AsyncSession, subject_id: int, limit: int = 50
) -> list[CorpusItem]:
    rows = await session.scalars(
        select(CorpusItem)
        .where(CorpusItem.subject_id == subject_id, CorpusItem.summary.is_(None))
        .order_by(CorpusItem.created_at.asc())
        .limit(limit)
    )
    return list(rows.all())
