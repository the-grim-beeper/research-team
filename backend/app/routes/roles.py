from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.role import RoleRead
from app.services.roles import list_roles

router = APIRouter(prefix="/api/v1/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
async def list_endpoint(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[RoleRead]:
    rows = await list_roles(session)
    return [
        RoleRead(
            id=r.id,
            slug=r.slug,
            display_name=r.display_name,
            category=r.category,
            default_system_prompt=r.default_system_prompt,
            default_model=r.default_model,
            default_cycle=r.default_cycle,
            default_tier=r.default_tier,
            tools=r.tools,
            created_at=r.created_at,
        )
        for r in rows
    ]
