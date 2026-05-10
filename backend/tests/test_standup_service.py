from app.services import standup
from app.services.openrouter import ChatResult
from app.services.subjects import create_subject
from app.services.users import ensure_admin_user


async def _setup(session_factory):
    async with session_factory() as s:
        user = await ensure_admin_user(s, email="t@test.com", password="pw")
        sub = await create_subject(s, user_id=user.id, title="T", brief="")
    return user.id, sub.id


def _stub_chat_with_responses(responses):
    iter_responses = iter(responses)

    async def fn(messages, *, model, max_tokens):
        try:
            return next(iter_responses)
        except StopIteration:
            return ChatResult(text="(default)", prompt_tokens=10, completion_tokens=5, raw={})

    return fn


async def test_run_standup_produces_four_artifacts(session_factory):
    uid, sid = await _setup(session_factory)

    responses = [
        # Editor: primary, then summary follow-up
        ChatResult(text="Briefing body", prompt_tokens=300, completion_tokens=200, raw={}),
        ChatResult(text="brief sum", prompt_tokens=20, completion_tokens=10, raw={}),
        # Critic
        ChatResult(text="Critique body", prompt_tokens=300, completion_tokens=150, raw={}),
        ChatResult(text="crit sum", prompt_tokens=20, completion_tokens=10, raw={}),
        # Contrarian
        ChatResult(text="Contrarian body", prompt_tokens=300, completion_tokens=150, raw={}),
        ChatResult(text="contra sum", prompt_tokens=20, completion_tokens=10, raw={}),
        # Question Generator
        ChatResult(text="Open questions", prompt_tokens=200, completion_tokens=100, raw={}),
        ChatResult(text="qg sum", prompt_tokens=20, completion_tokens=10, raw={}),
    ]
    chat = _stub_chat_with_responses(responses)

    async with session_factory() as s:
        artifacts = await standup.run_standup(
            s, subject_id=sid, user_id=uid, chat_fn=chat
        )

    assert [a.kind for a in artifacts] == ["briefing", "critique", "roundtable_post", "open_question"]
    assert "Briefing body" in artifacts[0].body_md
