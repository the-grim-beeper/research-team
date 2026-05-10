from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryEntry


async def recent_entries(
    session: AsyncSession, agent_id: int, limit: int = 20
) -> list[MemoryEntry]:
    rows = await session.scalars(
        select(MemoryEntry)
        .where(MemoryEntry.agent_id == agent_id)
        .order_by(MemoryEntry.created_at.desc())
        .limit(limit)
    )
    return list(rows.all())


async def append_entry(
    session: AsyncSession,
    *,
    agent_id: int,
    kind: str,
    content: str,
    importance: int = 3,
) -> MemoryEntry:
    entry = MemoryEntry(
        agent_id=agent_id,
        kind=kind,
        content=content,
        importance=importance,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry
