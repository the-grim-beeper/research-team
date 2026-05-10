from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.role import Role
from app.models.subject import Subject

VALID_CYCLES = {"off", "on_demand", "hourly", "every_4h", "daily"}


class InvalidAgentSettings(Exception):
    """Raised when proposed agent settings would be invalid."""


async def list_for_subject(session: AsyncSession, subject_id: int) -> list[Agent]:
    rows = await session.scalars(
        select(Agent).where(Agent.subject_id == subject_id).order_by(Agent.id)
    )
    return list(rows.all())


async def _agent_with_owner_check(
    session: AsyncSession, agent_id: int, user_id: int
) -> Agent:
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise LookupError(f"Agent {agent_id} not found")
    subject = await session.get(Subject, agent.subject_id)
    if subject is None or subject.user_id != user_id:
        raise LookupError(f"Agent {agent_id} not found")
    return agent


async def get_agent(session: AsyncSession, agent_id: int, user_id: int) -> Agent:
    return await _agent_with_owner_check(session, agent_id, user_id)


async def update_agent_settings(
    session: AsyncSession,
    agent_id: int,
    user_id: int,
    *,
    model: str | None = None,
    cycle: str | None = None,
    daily_budget_usd: Decimal | float | None = None,
    system_prompt_addendum: str | None = None,
) -> Agent:
    agent = await _agent_with_owner_check(session, agent_id, user_id)

    if cycle is not None:
        if cycle not in VALID_CYCLES:
            raise InvalidAgentSettings(
                f"Invalid cycle '{cycle}'. Valid: {sorted(VALID_CYCLES)}"
            )
        agent.cycle = cycle

    if model is not None:
        if not model.strip():
            raise InvalidAgentSettings("Model must be a non-empty string")
        agent.model = model.strip()

    if daily_budget_usd is not None:
        budget = Decimal(str(daily_budget_usd))
        if budget < 0:
            raise InvalidAgentSettings("daily_budget_usd must be ≥ 0")
        agent.daily_budget_usd = budget

    if system_prompt_addendum is not None:
        role = await session.get(Role, agent.role_id)
        if role is None:
            raise LookupError(f"Role {agent.role_id} not found")
        base = role.default_system_prompt
        addendum = system_prompt_addendum.strip()
        agent.system_prompt = f"{base}\n\n{addendum}".strip() if addendum else base

    await session.commit()
    await session.refresh(agent)
    return agent


async def spawn_default_team(session: AsyncSession, subject_id: int) -> list[Agent]:
    rows = await session.scalars(select(Role).order_by(Role.category, Role.id))
    roles = list(rows.all())
    now = datetime.now(timezone.utc)
    agents = [
        Agent(
            subject_id=subject_id,
            role_id=r.id,
            display_name=r.display_name,
            system_prompt=r.default_system_prompt,
            model=r.default_model,
            cycle=r.default_cycle,
            daily_budget_usd=Decimal("1.0"),
            spent_today_usd=Decimal("0"),
            created_at=now,
        )
        for r in roles
    ]
    session.add_all(agents)
    await session.commit()
    for a in agents:
        await session.refresh(a)
    return agents
