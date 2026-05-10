from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subject import Subject

ACTIVE_LIMIT = 3


class ActiveSubjectLimit(Exception):
    """Raised when creating a new active subject would exceed the per-user cap."""


async def _count_active(session: AsyncSession, user_id: int) -> int:
    rows = await session.scalars(
        select(Subject).where(Subject.user_id == user_id, Subject.status == "active")
    )
    return len(rows.all())


async def create_subject(session: AsyncSession, user_id: int, title: str, brief: str) -> Subject:
    if await _count_active(session, user_id) >= ACTIVE_LIMIT:
        raise ActiveSubjectLimit(f"At most {ACTIVE_LIMIT} active subjects allowed")
    subject = Subject(
        user_id=user_id,
        title=title,
        brief=brief,
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    session.add(subject)
    await session.commit()
    await session.refresh(subject)
    return subject


async def list_subjects(
    session: AsyncSession, user_id: int, status: str | None = None
) -> list[Subject]:
    stmt = select(Subject).where(Subject.user_id == user_id).order_by(Subject.created_at.desc())
    if status is not None:
        stmt = stmt.where(Subject.status == status)
    rows = await session.scalars(stmt)
    return list(rows.all())


async def archive_subject(session: AsyncSession, user_id: int, subject_id: int) -> Subject:
    subject = await session.get(Subject, subject_id)
    if subject is None or subject.user_id != user_id:
        raise LookupError(f"Subject {subject_id} not found")
    subject.status = "archived"
    await session.commit()
    await session.refresh(subject)
    return subject
