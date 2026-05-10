from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.artifact import Artifact
from app.models.user import User
from app.schemas.artifact import ArtifactRead
from app.services import artifacts as artifact_service
from app.services.subjects import get_subject

router = APIRouter(prefix="/api/v1", tags=["artifacts"])


class ArtifactCreateUser(BaseModel):
    kind: str = "instruction"
    title: str = ""
    body_md: str
    addressed_to: int | None = None
    parent_id: int | None = None


def _to_read(a: Artifact) -> ArtifactRead:
    return ArtifactRead(
        id=a.id,
        subject_id=a.subject_id,
        kind=a.kind,
        author_type=a.author_type,
        author_id=a.author_id,
        parent_id=a.parent_id,
        addressed_to=a.addressed_to,
        title=a.title,
        body_md=a.body_md,
        metadata_json=a.metadata_json,
        created_at=a.created_at,
    )


@router.get("/subjects/{subject_id}/artifacts", response_model=list[ArtifactRead])
async def list_for_subject(
    subject_id: int,
    limit: int = 50,
    kind: str | None = None,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ArtifactRead]:
    try:
        await get_subject(session, user_id=current.id, subject_id=subject_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    if kind:
        kinds = [k.strip() for k in kind.split(",") if k.strip()]
        rows_q = await session.scalars(
            select(Artifact)
            .where(Artifact.subject_id == subject_id, Artifact.kind.in_(kinds))
            .order_by(Artifact.created_at.desc())
            .limit(limit)
        )
        return [_to_read(a) for a in rows_q.all()]
    rows = await artifact_service.list_for_subject(session, subject_id, limit=limit)
    return [_to_read(a) for a in rows]


@router.post(
    "/subjects/{subject_id}/artifacts", response_model=ArtifactRead, status_code=201
)
async def create_user_artifact(
    subject_id: int,
    payload: ArtifactCreateUser,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ArtifactRead:
    try:
        await get_subject(session, user_id=current.id, subject_id=subject_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    art = await artifact_service.create(
        session,
        subject_id=subject_id,
        kind=payload.kind,
        author_type="user",
        author_id=None,
        title=payload.title,
        body_md=payload.body_md,
        parent_id=payload.parent_id,
        addressed_to=payload.addressed_to,
    )
    return _to_read(art)
