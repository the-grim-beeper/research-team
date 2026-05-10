from app.services import artifacts as artifact_service
from app.services.subjects import create_subject
from app.services.users import ensure_admin_user


async def _subject_id(session_factory) -> int:
    async with session_factory() as s:
        user = await ensure_admin_user(s, email="t@test.com", password="pw")
        sub = await create_subject(s, user_id=user.id, title="T", brief="")
        return sub.id


async def test_create_and_list(session_factory):
    sid = await _subject_id(session_factory)
    async with session_factory() as s:
        a1 = await artifact_service.create(
            s, subject_id=sid, kind="note", author_type="user", author_id=None,
            body_md="first", title="t1",
        )
        a2 = await artifact_service.create(
            s, subject_id=sid, kind="note", author_type="agent", author_id=1,
            body_md="second",
        )
        rows = await artifact_service.list_for_subject(s, sid)
    assert [r.id for r in rows] == [a2.id, a1.id]
    assert rows[0].body_md == "second"
