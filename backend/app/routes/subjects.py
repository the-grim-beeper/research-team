from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.subject import SubjectCreate, SubjectRead
from app.services.subjects import (
    ActiveSubjectLimit,
    archive_subject,
    create_subject,
    list_subjects,
)

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


def _to_read(s) -> SubjectRead:
    return SubjectRead(
        id=s.id, title=s.title, brief=s.brief, status=s.status, created_at=s.created_at
    )


@router.get("", response_model=list[SubjectRead])
async def list_endpoint(
    status: str | None = None,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[SubjectRead]:
    rows = await list_subjects(session, user_id=current.id, status=status)
    return [_to_read(s) for s in rows]


@router.post("", response_model=SubjectRead, status_code=201)
async def create_endpoint(
    payload: SubjectCreate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubjectRead:
    try:
        s = await create_subject(session, user_id=current.id, title=payload.title, brief=payload.brief)
    except ActiveSubjectLimit as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from e
    return _to_read(s)


@router.post("/{subject_id}/archive", response_model=SubjectRead)
async def archive_endpoint(
    subject_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubjectRead:
    try:
        s = await archive_subject(session, user_id=current.id, subject_id=subject_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return _to_read(s)
