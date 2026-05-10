import pytest

from app.services.subjects import (
    ActiveSubjectLimit,
    archive_subject,
    create_subject,
    list_subjects,
)


async def test_create_and_list_subject(session_factory):
    async with session_factory() as s:
        sub = await create_subject(s, user_id=1, title="AI governance", brief="Trends.")
        assert sub.id is not None
        assert sub.status == "active"
        rows = await list_subjects(s, user_id=1)
    assert [r.title for r in rows] == ["AI governance"]


async def test_three_active_limit(session_factory):
    async with session_factory() as s:
        for i in range(3):
            await create_subject(s, user_id=1, title=f"S{i}", brief="")
        with pytest.raises(ActiveSubjectLimit):
            await create_subject(s, user_id=1, title="S4", brief="")


async def test_archiving_frees_a_slot(session_factory):
    async with session_factory() as s:
        first = await create_subject(s, user_id=1, title="S0", brief="")
        for i in range(1, 3):
            await create_subject(s, user_id=1, title=f"S{i}", brief="")
        await archive_subject(s, user_id=1, subject_id=first.id)
        await create_subject(s, user_id=1, title="S3", brief="")
        rows = await list_subjects(s, user_id=1, status="active")
    titles = sorted(r.title for r in rows)
    assert titles == ["S1", "S2", "S3"]


async def test_archive_unknown_raises(session_factory):
    async with session_factory() as s:
        with pytest.raises(LookupError):
            await archive_subject(s, user_id=1, subject_id=999)
