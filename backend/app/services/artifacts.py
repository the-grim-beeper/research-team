from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact


async def create(
    session: AsyncSession,
    *,
    subject_id: int,
    kind: str,
    author_type: str,
    author_id: int | None,
    body_md: str,
    title: str = "",
    parent_id: int | None = None,
    addressed_to: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> Artifact:
    art = Artifact(
        subject_id=subject_id,
        kind=kind,
        author_type=author_type,
        author_id=author_id,
        parent_id=parent_id,
        addressed_to=addressed_to,
        title=title,
        body_md=body_md,
        metadata_json=metadata or {},
        created_at=datetime.now(timezone.utc),
    )
    session.add(art)
    await session.commit()
    await session.refresh(art)
    return art


async def list_for_subject(
    session: AsyncSession, subject_id: int, limit: int = 50
) -> list[Artifact]:
    rows = await session.scalars(
        select(Artifact)
        .where(Artifact.subject_id == subject_id)
        .order_by(Artifact.created_at.desc())
        .limit(limit)
    )
    return list(rows.all())


async def get(session: AsyncSession, artifact_id: int) -> Artifact | None:
    return await session.get(Artifact, artifact_id)
