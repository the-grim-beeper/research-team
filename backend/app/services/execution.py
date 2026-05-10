from datetime import datetime, timezone
from decimal import Decimal
from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import Agent
from app.models.artifact import Artifact
from app.pricing import estimate_cost
from app.services import artifacts as artifact_service
from app.services import memory as memory_service
from app.services import openrouter
from app.services.agents import get_agent

# Type alias for a chat function — lets tests inject a stub.
ChatFn = Callable[..., Awaitable[openrouter.ChatResult]]


class BudgetExceeded(Exception):
    """Raised when the agent's daily budget cap is reached."""


def _today(now: datetime) -> tuple[int, int, int]:
    return (now.year, now.month, now.day)


def _maybe_reset_budget(agent: Agent, now: datetime) -> None:
    if agent.last_run_at is None or _today(agent.last_run_at) < _today(now):
        agent.spent_today_usd = Decimal("0")


def _build_messages(
    agent: Agent,
    memory_text: str,
    instruction: str,
    extra_system_context: str | None = None,
) -> list[dict[str, str]]:
    memory_block = memory_text or "(no prior memory)"
    messages: list[dict[str, str]] = [{"role": "system", "content": agent.system_prompt}]
    if extra_system_context:
        messages.append({"role": "system", "content": extra_system_context})
    messages.append(
        {
            "role": "system",
            "content": "Your private memory (most recent first):\n" + memory_block,
        }
    )
    messages.append({"role": "user", "content": instruction})
    return messages


def _format_memory(entries) -> str:
    return "\n".join(
        f"- [{e.kind}] {e.content}" for e in entries
    )


async def run_agent_once(
    session: AsyncSession,
    *,
    agent_id: int,
    user_id: int,
    user_instruction: str | None = None,
    artifact_kind: str = "note",
    extra_system_context: str | None = None,
    chat_fn: ChatFn | None = None,
) -> Artifact:
    if chat_fn is None:
        chat_fn = openrouter.chat
    agent = await get_agent(session, agent_id=agent_id, user_id=user_id)

    now = datetime.now(timezone.utc)
    _maybe_reset_budget(agent, now)

    if agent.spent_today_usd >= agent.daily_budget_usd:
        raise BudgetExceeded(
            f"Agent has already spent ${agent.spent_today_usd}; "
            f"cap is ${agent.daily_budget_usd}"
        )

    entries = await memory_service.recent_entries(session, agent.id, limit=20)
    memory_text = _format_memory(entries)

    instruction = user_instruction or (
        "Run your normal cycle responsibilities. Produce one short note "
        "(≤400 words) on the most useful thing you can do right now given "
        "your role and prior memory."
    )

    messages = _build_messages(agent, memory_text, instruction, extra_system_context)

    result = await chat_fn(
        messages,
        model=agent.model,
        max_tokens=settings.max_tokens_default,
    )
    primary_cost = estimate_cost(agent.model, result.prompt_tokens, result.completion_tokens)

    summary_messages = [
        {
            "role": "system",
            "content": (
                "Given the following text, write ONE short sentence (≤30 words) "
                "summarizing the most important thing the author should remember "
                "for future reference. Reply with the sentence only."
            ),
        },
        {"role": "user", "content": result.text or "(empty response)"},
    ]
    summary_cost = Decimal("0")
    summary_text = ""
    try:
        summary = await chat_fn(
            summary_messages, model=settings.summary_model, max_tokens=80
        )
        summary_text = (summary.text or "").strip()
        summary_cost = estimate_cost(
            settings.summary_model, summary.prompt_tokens, summary.completion_tokens
        )
    except openrouter.OpenRouterError:
        # Don't let a flaky summary call kill the primary result.
        summary_text = ""

    agent.spent_today_usd = (Decimal(str(agent.spent_today_usd)) + primary_cost + summary_cost).quantize(Decimal("0.0001"))
    agent.last_run_at = now
    await session.commit()

    artifact = await artifact_service.create(
        session,
        subject_id=agent.subject_id,
        kind=artifact_kind,
        author_type="agent",
        author_id=agent.id,
        body_md=result.text,
        metadata={
            "model": agent.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "cost_usd": str(primary_cost),
            "summary_cost_usd": str(summary_cost),
            "user_instruction": user_instruction,
        },
    )

    if summary_text:
        await memory_service.append_entry(
            session,
            agent_id=agent.id,
            kind="note",
            content=summary_text,
            importance=3,
        )

    return artifact
