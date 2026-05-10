from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.artifact import Artifact
from app.models.user import User
from app.schemas.artifact import ArtifactRead
from app.services import artifacts as artifact_service
from app.services.subjects import get_subject

router = APIRouter(prefix="/api/v1", tags=["artifacts"])


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
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ArtifactRead]:
    try:
        await get_subject(session, user_id=current.id, subject_id=subject_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    rows = await artifact_service.list_for_subject(session, subject_id, limit=limit)
    return [_to_read(a) for a in rows]
