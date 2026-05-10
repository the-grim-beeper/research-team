from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.corpus import CorpusItem
from app.models.user import User
from app.schemas.bibliography import (
    BibliographyEntryRead,
    CommentAppend,
    TextNote,
    UrlIngest,
)
from app.schemas.corpus import CorpusItemRead
from app.schemas.source import SourceCreate, SourceRead
from app.services import bibliography as bib_service
from app.services import corpus as corpus_service
from app.services import ingestion
from app.services import sources as source_service
from app.services.librarian import process_new_for_subject
from app.services.subjects import get_subject

router = APIRouter(prefix="/api/v1", tags=["library"])


def _source_read(s) -> SourceRead:
    return SourceRead(
        id=s.id,
        subject_id=s.subject_id,
        kind=s.kind,
        display_name=s.display_name,
        config_json=s.config_json,
        created_at=s.created_at,
    )


def _corpus_read(c: CorpusItem) -> CorpusItemRead:
    return CorpusItemRead(
        id=c.id,
        subject_id=c.subject_id,
        source_id=c.source_id,
        external_id=c.external_id,
        title=c.title,
        authors_json=c.authors_json,
        published_at=c.published_at,
        url=c.url,
        summary=c.summary,
        tags_json=c.tags_json,
        importance=c.importance,
        created_at=c.created_at,
    )


def _bibliography_read(entry, item) -> BibliographyEntryRead:
    return BibliographyEntryRead(
        id=entry.id,
        subject_id=entry.subject_id,
        corpus_item_id=entry.corpus_item_id,
        comments=entry.comments,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        title=item.title,
        url=item.url,
        authors=item.authors_json,
        summary=item.summary,
        tags=item.tags_json,
        importance=item.importance,
    )


async def _check_subject(session: AsyncSession, user_id: int, subject_id: int) -> None:
    try:
        await get_subject(session, user_id=user_id, subject_id=subject_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e


@router.post(
    "/subjects/{subject_id}/sources", response_model=SourceRead, status_code=201
)
async def create_source(
    subject_id: int,
    payload: SourceCreate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SourceRead:
    await _check_subject(session, current.id, subject_id)
    try:
        s = await source_service.register(
            session,
            subject_id=subject_id,
            kind=payload.kind,
            config=payload.config,
            display_name=payload.display_name,
        )
    except source_service.InvalidSource as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    return _source_read(s)


@router.get("/subjects/{subject_id}/sources", response_model=list[SourceRead])
async def list_sources(
    subject_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SourceRead]:
    await _check_subject(session, current.id, subject_id)
    rows = await source_service.list_for_subject(session, subject_id)
    return [_source_read(s) for s in rows]


@router.delete("/sources/{source_id}", status_code=204)
async def remove_source(
    source_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    src = await source_service.get(session, source_id)
    if src is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    await _check_subject(session, current.id, src.subject_id)
    await source_service.delete(session, source_id)


async def _fetch_for_source(src) -> list[dict]:
    if src.kind == "rss":
        return await ingestion.fetch_rss(src.config_json["url"])
    if src.kind == "arxiv":
        return await ingestion.fetch_arxiv(
            src.config_json["query"],
            max_results=int(src.config_json.get("max_results", 20)),
        )
    if src.kind == "url":
        return await ingestion.fetch_url(src.config_json["url"])
    if src.kind == "notes":
        return []
    return []


@router.post(
    "/subjects/{subject_id}/sources/{source_id}/ingest",
    response_model=list[BibliographyEntryRead],
)
async def ingest_source(
    subject_id: int,
    source_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BibliographyEntryRead]:
    await _check_subject(session, current.id, subject_id)
    src = await source_service.get(session, source_id)
    if src is None or src.subject_id != subject_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")

    try:
        items = await _fetch_for_source(src)
    except Exception as e:  # network / parse errors
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Fetch failed: {e}") from e

    new_items = await source_service.persist_new_items(
        session, subject_id=subject_id, source_id=source_id, items=items
    )
    if not new_items:
        return []

    entries = await process_new_for_subject(
        session, subject_id=subject_id, max_items=len(new_items)
    )
    pairs = await bib_service.list_for_subject(session, subject_id)
    by_id = {e.id: (e, item) for (e, item) in pairs}
    return [_bibliography_read(e, item) for e in entries for (e, item) in [by_id.get(e.id, (e, None))] if item]


@router.post("/subjects/{subject_id}/notes", response_model=list[BibliographyEntryRead])
async def add_note(
    subject_id: int,
    payload: TextNote,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BibliographyEntryRead]:
    await _check_subject(session, current.id, subject_id)
    item = ingestion.make_text_item(payload.text, title=payload.title)
    new_items = await source_service.persist_new_items(
        session, subject_id=subject_id, source_id=None, items=[item]
    )
    if not new_items:
        return []
    entries = await process_new_for_subject(session, subject_id=subject_id, max_items=1)
    pairs = await bib_service.list_for_subject(session, subject_id)
    by_id = {e.id: (e, item) for (e, item) in pairs}
    return [
        _bibliography_read(e, item)
        for e in entries
        for (e, item) in [by_id.get(e.id, (e, None))]
        if item
    ]


@router.post("/subjects/{subject_id}/url", response_model=list[BibliographyEntryRead])
async def add_url(
    subject_id: int,
    payload: UrlIngest,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BibliographyEntryRead]:
    await _check_subject(session, current.id, subject_id)
    try:
        items = await ingestion.fetch_url(payload.url)
    except Exception as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Fetch failed: {e}") from e
    new_items = await source_service.persist_new_items(
        session, subject_id=subject_id, source_id=None, items=items
    )
    if not new_items:
        return []
    entries = await process_new_for_subject(session, subject_id=subject_id, max_items=1)
    pairs = await bib_service.list_for_subject(session, subject_id)
    by_id = {e.id: (e, item) for (e, item) in pairs}
    return [
        _bibliography_read(e, item)
        for e in entries
        for (e, item) in [by_id.get(e.id, (e, None))]
        if item
    ]


@router.get("/subjects/{subject_id}/corpus", response_model=list[CorpusItemRead])
async def list_corpus(
    subject_id: int,
    limit: int = 100,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CorpusItemRead]:
    await _check_subject(session, current.id, subject_id)
    rows = await corpus_service.list_for_subject(session, subject_id, limit=limit)
    return [_corpus_read(c) for c in rows]


@router.get(
    "/subjects/{subject_id}/bibliography", response_model=list[BibliographyEntryRead]
)
async def list_bibliography(
    subject_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BibliographyEntryRead]:
    await _check_subject(session, current.id, subject_id)
    pairs = await bib_service.list_for_subject(session, subject_id)
    return [_bibliography_read(e, c) for (e, c) in pairs]


@router.post("/bibliography/{entry_id}/comment", response_model=BibliographyEntryRead)
async def comment_endpoint(
    entry_id: int,
    payload: CommentAppend,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BibliographyEntryRead:
    from app.models.bibliography import BibliographyEntry

    entry = await session.get(BibliographyEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "BibliographyEntry not found")
    await _check_subject(session, current.id, entry.subject_id)
    updated = await bib_service.append_comment(session, entry_id, payload.comment)
    item = await session.get(CorpusItem, updated.corpus_item_id)
    return _bibliography_read(updated, item)
