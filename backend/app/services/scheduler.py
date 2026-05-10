"""APScheduler-driven cycle engine.

The scheduler runs in-process inside the FastAPI lifespan. It owns one job per
agent (id `agent-{N}`) plus one daily reset job. State lives in memory; on
restart we re-sync from DB via `reload_all`.

Tests don't start the scheduler; the module-level `_scheduler` stays None,
which makes `schedule_agent` / `unschedule_agent` no-op safely.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import Agent
from app.models.subject import Subject

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None
_session_provider: Callable[[], "AbstractAsyncSessionContext"] | None = None

DAILY_RESET_JOB_ID = "daily-budget-reset"


def _job_id(agent_id: int) -> str:
    return f"agent-{agent_id}"


def _cron_for_cycle(cycle: str) -> CronTrigger | None:
    if cycle == "hourly":
        return CronTrigger(minute=0)
    if cycle == "every_4h":
        return CronTrigger(minute=0, hour="0,4,8,12,16,20")
    if cycle == "daily":
        return CronTrigger(minute=0, hour=settings.daily_run_hour_utc)
    return None


@asynccontextmanager
async def _session():
    assert _session_provider is not None
    async with _session_provider() as s:  # type: ignore[misc]
        yield s


async def _tick(agent_id: int) -> None:
    """Cron-fired job — run one cycle for an agent. Errors are logged, not raised."""
    from app.services.execution import BudgetExceeded, run_agent_once
    from app.services.openrouter import OpenRouterError

    try:
        async with _session() as session:
            agent = await session.get(Agent, agent_id)
            if agent is None:
                logger.info("Tick skipped: agent %s not found", agent_id)
                return
            subject = await session.get(Subject, agent.subject_id)
            if subject is None or subject.status != "active":
                logger.info("Tick skipped: subject inactive for agent %s", agent_id)
                return
            try:
                await run_agent_once(
                    session,
                    agent_id=agent_id,
                    user_id=subject.user_id,
                    user_instruction=None,
                )
            except BudgetExceeded:
                logger.info("Agent %s over budget; skipping tick", agent_id)
            except OpenRouterError as e:
                logger.warning("OpenRouter error in tick for agent %s: %s", agent_id, e)
    except Exception:  # noqa: BLE001  defensive — never crash the scheduler thread
        logger.exception("Unhandled error in agent tick %s", agent_id)


async def _daily_reset_tick() -> None:
    try:
        async with _session() as session:
            rows = await session.scalars(select(Agent))
            for a in rows.all():
                a.spent_today_usd = Decimal("0")
            await session.commit()
        logger.info("Daily budget reset complete")
    except Exception:  # noqa: BLE001
        logger.exception("Daily reset failed")


def schedule_agent(agent: Agent) -> None:
    """Add or replace the job for this agent based on its cycle."""
    if _scheduler is None:
        return
    job_id = _job_id(agent.id)
    trigger = _cron_for_cycle(agent.cycle)
    if trigger is None:
        try:
            _scheduler.remove_job(job_id)
        except Exception:  # noqa: BLE001  job not found is fine
            pass
        return
    _scheduler.add_job(
        _tick,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        args=[agent.id],
        misfire_grace_time=300,
        coalesce=True,
    )


def unschedule_agent(agent_id: int) -> None:
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(_job_id(agent_id))
    except Exception:  # noqa: BLE001
        pass


async def reload_all(session: AsyncSession) -> int:
    """Sync the schedule with DB state. Returns number of jobs registered."""
    if _scheduler is None:
        return 0
    rows = await session.scalars(
        select(Agent)
        .join(Subject, Subject.id == Agent.subject_id)
        .where(Subject.status == "active")
    )
    count = 0
    for agent in rows.all():
        if _cron_for_cycle(agent.cycle) is None:
            continue
        schedule_agent(agent)
        count += 1
    return count


async def start(session_provider: Callable[[], Any]) -> None:
    global _scheduler, _session_provider
    if _scheduler is not None:
        return
    _session_provider = session_provider
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _daily_reset_tick,
        trigger=CronTrigger(minute=0, hour=0),
        id=DAILY_RESET_JOB_ID,
        replace_existing=True,
        misfire_grace_time=600,
        coalesce=True,
    )
    _scheduler.start()
    async with session_provider() as s:
        await reload_all(s)
    logger.info("Scheduler started")


async def shutdown() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Scheduler shut down")


# Used as a sentinel for the type hint above.
class AbstractAsyncSessionContext:
    async def __aenter__(self) -> AsyncSession: ...  # pragma: no cover
    async def __aexit__(self, *exc: object) -> None: ...  # pragma: no cover
