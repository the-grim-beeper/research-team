from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corpus import CorpusItem
from app.models.source import Source

VALID_KINDS = {"rss", "arxiv", "url", "notes"}


class InvalidSource(Exception):
    pass


async def register(
    session: AsyncSession,
    *,
    subject_id: int,
    kind: str,
    config: dict[str, Any],
    display_name: str,
) -> Source:
    if kind not in VALID_KINDS:
        raise InvalidSource(f"Unknown source kind: {kind}")
    src = Source(
        subject_id=subject_id,
        kind=kind,
        display_name=display_name or kind,
        config_json=config,
        created_at=datetime.now(timezone.utc),
    )
    session.add(src)
    await session.commit()
    await session.refresh(src)
    return src


async def list_for_subject(session: AsyncSession, subject_id: int) -> list[Source]:
    rows = await session.scalars(
        select(Source).where(Source.subject_id == subject_id).order_by(Source.id)
    )
    return list(rows.all())


async def get(session: AsyncSession, source_id: int) -> Source | None:
    return await session.get(Source, source_id)


async def delete(session: AsyncSession, source_id: int) -> None:
    src = await session.get(Source, source_id)
    if src is None:
        raise LookupError(f"Source {source_id} not found")
    await session.delete(src)
    await session.commit()


async def persist_new_items(
    session: AsyncSession,
    *,
    subject_id: int,
    source_id: int | None,
    items: list[dict[str, Any]],
) -> list[CorpusItem]:
    """Insert items not yet present (dedup by subject + source + external_id)."""
    if not items:
        return []

    existing_ids = await session.scalars(
        select(CorpusItem.external_id).where(
            CorpusItem.subject_id == subject_id,
            CorpusItem.source_id == source_id,
        )
    )
    existing = set(existing_ids.all())

    new_rows: list[CorpusItem] = []
    now = datetime.now(timezone.utc)
    for item in items:
        ext = item.get("external_id")
        if ext and ext in existing:
            continue
        ci = CorpusItem(
            subject_id=subject_id,
            source_id=source_id,
            external_id=ext,
            title=item.get("title") or "",
            authors_json=item.get("authors") or [],
            published_at=item.get("published_at"),
            url=item.get("url"),
            text=item.get("text") or "",
            tags_json=[],
            created_at=now,
        )
        new_rows.append(ci)
    if new_rows:
        session.add_all(new_rows)
        await session.commit()
        for r in new_rows:
            await session.refresh(r)
    return new_rows
