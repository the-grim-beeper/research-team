from decimal import Decimal

import pytest

from app.services import execution
from app.services.agents import list_for_subject, update_agent_settings
from app.services.subjects import create_subject
from app.services.users import ensure_admin_user
from app.services.openrouter import ChatResult


def _stub_chat(text: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    async def fn(messages, *, model, max_tokens):
        return ChatResult(
            text=text, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, raw={},
        )
    return fn


async def _setup(session_factory):
    async with session_factory() as s:
        user = await ensure_admin_user(s, email="t@test.com", password="pw")
        sub = await create_subject(s, user_id=user.id, title="T", brief="")
        agents = await list_for_subject(s, subject_id=sub.id)
    return user.id, sub.id, agents[0].id


async def test_run_creates_artifact_and_memory_and_updates_budget(session_factory):
    uid, sid, aid = await _setup(session_factory)

    chats = [
        ChatResult(text="primary output", prompt_tokens=200, completion_tokens=100, raw={}),
        ChatResult(text="summary line", prompt_tokens=50, completion_tokens=10, raw={}),
    ]

    async def stub(messages, *, model, max_tokens):
        return chats.pop(0)

    async with session_factory() as s:
        artifact = await execution.run_agent_once(
            s, agent_id=aid, user_id=uid, user_instruction="hello", chat_fn=stub
        )

    assert artifact.body_md == "primary output"
    assert artifact.author_type == "agent"
    assert artifact.author_id == aid
    assert "model" in artifact.metadata_json

    async with session_factory() as s:
        from app.services import memory as memory_service
        from app.models.agent import Agent

        entries = await memory_service.recent_entries(s, aid)
        assert any("summary line" in e.content for e in entries)

        agent = await s.get(Agent, aid)
        assert float(agent.spent_today_usd) > 0
        assert agent.last_run_at is not None


async def test_budget_exceeded_raises(session_factory):
    uid, sid, aid = await _setup(session_factory)

    async with session_factory() as s:
        # Set budget to zero so any spend fails the precondition.
        await update_agent_settings(s, agent_id=aid, user_id=uid, daily_budget_usd=Decimal("0"))

    # Now spend a token to push spent_today_usd > 0 in DB so the check trips.
    async with session_factory() as s:
        from app.models.agent import Agent
        agent = await s.get(Agent, aid)
        agent.spent_today_usd = Decimal("0.0001")
        await s.commit()

    async with session_factory() as s:
        with pytest.raises(execution.BudgetExceeded):
            await execution.run_agent_once(
                s, agent_id=aid, user_id=uid, user_instruction="hi",
                chat_fn=_stub_chat("nope"),
            )


async def test_unknown_agent_returns_lookup_error(session_factory):
    uid, sid, _ = await _setup(session_factory)
    async with session_factory() as s:
        with pytest.raises(LookupError):
            await execution.run_agent_once(
                s, agent_id=9999, user_id=uid, chat_fn=_stub_chat("x"),
            )
