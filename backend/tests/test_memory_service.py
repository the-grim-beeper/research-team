from app.services import memory as memory_service
from app.services.agents import list_for_subject
from app.services.subjects import create_subject
from app.services.users import ensure_admin_user


async def _agent_id(session_factory) -> int:
    async with session_factory() as s:
        user = await ensure_admin_user(s, email="t@test.com", password="pw")
        sub = await create_subject(s, user_id=user.id, title="T", brief="")
        agents = await list_for_subject(s, subject_id=sub.id)
        return agents[0].id


async def test_append_and_recent(session_factory):
    aid = await _agent_id(session_factory)
    async with session_factory() as s:
        for i in range(3):
            await memory_service.append_entry(
                s, agent_id=aid, kind="note", content=f"entry {i}", importance=2
            )
        rows = await memory_service.recent_entries(s, aid, limit=10)
    assert [r.content for r in rows] == ["entry 2", "entry 1", "entry 0"]
