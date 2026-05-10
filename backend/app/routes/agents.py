from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_session
from app.models.agent import Agent
from app.models.role import Role
from app.models.user import User
from app.schemas.agent import AgentRead, AgentUpdate
from app.schemas.role import RoleEmbed
from app.services.agents import (
    InvalidAgentSettings,
    get_agent,
    list_for_subject,
    update_agent_settings,
)
from app.services.subjects import get_subject

router = APIRouter(prefix="/api/v1", tags=["agents"])


async def _to_read(session: AsyncSession, agent: Agent) -> AgentRead:
    role = await session.get(Role, agent.role_id)
    assert role is not None
    return AgentRead(
        id=agent.id,
        subject_id=agent.subject_id,
        role=RoleEmbed(
            id=role.id, slug=role.slug, display_name=role.display_name, category=role.category
        ),
        display_name=agent.display_name,
        system_prompt=agent.system_prompt,
        model=agent.model,
        cycle=agent.cycle,
        daily_budget_usd=agent.daily_budget_usd,
        spent_today_usd=agent.spent_today_usd,
        last_run_at=agent.last_run_at,
        created_at=agent.created_at,
    )


@router.get("/subjects/{subject_id}/agents", response_model=list[AgentRead])
async def list_agents_for_subject(
    subject_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AgentRead]:
    try:
        await get_subject(session, user_id=current.id, subject_id=subject_id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    agents = await list_for_subject(session, subject_id=subject_id)
    return [await _to_read(session, a) for a in agents]


@router.get("/agents/{agent_id}", response_model=AgentRead)
async def get_agent_endpoint(
    agent_id: int,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgentRead:
    try:
        agent = await get_agent(session, agent_id=agent_id, user_id=current.id)
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    return await _to_read(session, agent)


@router.patch("/agents/{agent_id}", response_model=AgentRead)
async def patch_agent(
    agent_id: int,
    payload: AgentUpdate,
    current: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AgentRead:
    try:
        agent = await update_agent_settings(
            session,
            agent_id=agent_id,
            user_id=current.id,
            model=payload.model,
            cycle=payload.cycle,
            daily_budget_usd=payload.daily_budget_usd,
            system_prompt_addendum=payload.system_prompt_addendum,
        )
    except LookupError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
    except InvalidAgentSettings as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    return await _to_read(session, agent)
