from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.user import User
from app.routes.artifacts import _to_read
from app.schemas.artifact import ArtifactRead
from app.services.openrouter import OpenRouterError
from app.services.standup import run_standup
from app.services.subjects import get_subject

router = APIRouter(prefix="/api/v1", tags=["standup"])


@router.post("/subjects/{subject_id}/standup", response_model=list[ArtifactRead])
async def standup_endpoint(
    subject_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ArtifactRead]:
    try:
        await get_subject(session, user_id=current.id, subject_id=subject_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    try:
        artifacts = await run_standup(session, subject_id=subject_id, user_id=current.id)
    except OpenRouterError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    return [_to_read(a) for a in artifacts]
