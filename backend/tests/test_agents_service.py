import pytest

from app.services.agents import (
    InvalidAgentSettings,
    get_agent,
    list_for_subject,
    spawn_default_team,
    update_agent_settings,
)
from app.services.subjects import create_subject
from app.services.users import ensure_admin_user


async def _setup(session_factory):
    async with session_factory() as s:
        user = await ensure_admin_user(s, email="t@test.com", password="pw")
        sub = await create_subject(s, user_id=user.id, title="T", brief="")
    return user.id, sub.id


async def test_spawn_creates_eight_agents(session_factory):
    uid, sid = await _setup(session_factory)
    async with session_factory() as s:
        agents = await list_for_subject(s, subject_id=sid)
    # create_subject already spawns; ensure we don't double-spawn here
    assert len(agents) == 8


async def test_spawn_default_team_idempotent_via_create_subject(session_factory):
    """create_subject calls spawn_default_team once; calling spawn again duplicates."""
    uid, sid = await _setup(session_factory)
    async with session_factory() as s:
        await spawn_default_team(s, subject_id=sid)
        agents = await list_for_subject(s, subject_id=sid)
    assert len(agents) == 16  # documents non-idempotent behaviour


async def test_get_agent_owner_check(session_factory):
    uid, sid = await _setup(session_factory)
    async with session_factory() as s:
        agents = await list_for_subject(s, subject_id=sid)
        agent_id = agents[0].id

        a = await get_agent(s, agent_id=agent_id, user_id=uid)
        assert a.id == agent_id

        with pytest.raises(LookupError):
            await get_agent(s, agent_id=agent_id, user_id=uid + 999)


async def test_update_agent_validates_cycle(session_factory):
    uid, sid = await _setup(session_factory)
    async with session_factory() as s:
        agents = await list_for_subject(s, subject_id=sid)
        with pytest.raises(InvalidAgentSettings):
            await update_agent_settings(
                s, agent_id=agents[0].id, user_id=uid, cycle="weekly"
            )


async def test_update_agent_applies_addendum(session_factory):
    uid, sid = await _setup(session_factory)
    async with session_factory() as s:
        agents = await list_for_subject(s, subject_id=sid)
        original_prompt = agents[0].system_prompt

        updated = await update_agent_settings(
            s,
            agent_id=agents[0].id,
            user_id=uid,
            system_prompt_addendum="Additional rule: always cite primary sources.",
        )
        assert original_prompt in updated.system_prompt
        assert "Additional rule" in updated.system_prompt


async def test_update_agent_applies_model_and_budget(session_factory):
    uid, sid = await _setup(session_factory)
    async with session_factory() as s:
        agents = await list_for_subject(s, subject_id=sid)
        updated = await update_agent_settings(
            s,
            agent_id=agents[0].id,
            user_id=uid,
            model="openai/gpt-4o-mini",
            daily_budget_usd=2.5,
        )
    assert updated.model == "openai/gpt-4o-mini"
    assert float(updated.daily_budget_usd) == 2.5


async def test_update_agent_rejects_negative_budget(session_factory):
    uid, sid = await _setup(session_factory)
    async with session_factory() as s:
        agents = await list_for_subject(s, subject_id=sid)
        with pytest.raises(InvalidAgentSettings):
            await update_agent_settings(
                s, agent_id=agents[0].id, user_id=uid, daily_budget_usd=-1
            )
