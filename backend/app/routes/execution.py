from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.user import User
from app.routes.artifacts import _to_read
from app.schemas.artifact import ArtifactRead
from app.schemas.execution import ExecuteNowRequest
from app.services.execution import BudgetExceeded, run_agent_once
from app.services.openrouter import OpenRouterError

router = APIRouter(prefix="/api/v1", tags=["execution"])


@router.post("/agents/{agent_id}/execute", response_model=ArtifactRead)
async def execute_now(
    agent_id: int,
    payload: ExecuteNowRequest,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ArtifactRead:
    try:
        artifact = await run_agent_once(
            session,
            agent_id=agent_id,
            user_id=current.id,
            user_instruction=payload.instruction,
        )
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except BudgetExceeded as e:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, str(e)) from e
    except OpenRouterError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    return _to_read(artifact)
