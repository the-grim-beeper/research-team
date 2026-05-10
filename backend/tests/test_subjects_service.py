import pytest

from app.services.subjects import (
    ActiveSubjectLimit,
    archive_subject,
    create_subject,
    list_subjects,
)
from app.services.users import ensure_admin_user


async def _user_id(session_factory) -> int:
    async with session_factory() as s:
        user = await ensure_admin_user(s, email="t@test.com", password="pw")
        return user.id


async def test_create_and_list_subject(session_factory):
    uid = await _user_id(session_factory)
    async with session_factory() as s:
        sub = await create_subject(s, user_id=uid, title="AI governance", brief="Trends.")
        assert sub.id is not None
        assert sub.status == "active"
        rows = await list_subjects(s, user_id=uid)
    assert [r.title for r in rows] == ["AI governance"]


async def test_three_active_limit(session_factory):
    uid = await _user_id(session_factory)
    async with session_factory() as s:
        for i in range(3):
            await create_subject(s, user_id=uid, title=f"S{i}", brief="")
        with pytest.raises(ActiveSubjectLimit):
            await create_subject(s, user_id=uid, title="S4", brief="")


async def test_archiving_frees_a_slot(session_factory):
    uid = await _user_id(session_factory)
    async with session_factory() as s:
        first = await create_subject(s, user_id=uid, title="S0", brief="")
        for i in range(1, 3):
            await create_subject(s, user_id=uid, title=f"S{i}", brief="")
        await archive_subject(s, user_id=uid, subject_id=first.id)
        await create_subject(s, user_id=uid, title="S3", brief="")
        rows = await list_subjects(s, user_id=uid, status="active")
    titles = sorted(r.title for r in rows)
    assert titles == ["S1", "S2", "S3"]


async def test_archive_unknown_raises(session_factory):
    uid = await _user_id(session_factory)
    async with session_factory() as s:
        with pytest.raises(LookupError):
            await archive_subject(s, user_id=uid, subject_id=999)


async def test_create_subject_spawns_default_team(session_factory):
    uid = await _user_id(session_factory)
    async with session_factory() as s:
        sub = await create_subject(s, user_id=uid, title="Topic", brief="")
        from app.services.agents import list_for_subject

        agents = await list_for_subject(s, subject_id=sub.id)
    assert len(agents) == 8
    slugs_by_role = sorted(a.display_name for a in agents)
    assert "Librarian" in slugs_by_role
    assert "Contrarian" in slugs_by_role
    assert "Empiricist" in slugs_by_role
