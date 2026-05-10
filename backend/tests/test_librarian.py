from app.services import librarian, sources as source_service
from app.services.openrouter import ChatResult
from app.services.subjects import create_subject
from app.services.users import ensure_admin_user


def _stub_chat(responses):
    async def fn(messages, *, model, max_tokens):
        return responses.pop(0)
    return fn


async def _setup_with_item(session_factory):
    async with session_factory() as s:
        user = await ensure_admin_user(s, email="t@test.com", password="pw")
        sub = await create_subject(s, user_id=user.id, title="T", brief="")
        src = await source_service.register(
            s,
            subject_id=sub.id,
            kind="notes",
            config={},
            display_name="Notes",
        )
        new_items = await source_service.persist_new_items(
            s,
            subject_id=sub.id,
            source_id=src.id,
            items=[{
                "external_id": "ext-1",
                "title": "Item 1",
                "authors": ["You"],
                "published_at": None,
                "url": None,
                "text": "Some text body for the librarian to summarize.",
            }],
        )
    return sub.id, new_items[0].id


async def test_process_corpus_item_writes_summary_and_bibliography(session_factory):
    subject_id, item_id = await _setup_with_item(session_factory)
    chat = _stub_chat([
        ChatResult(
            text='{"summary": "Concise summary.", "tags": ["X","Y"], "importance": 4}',
            prompt_tokens=100, completion_tokens=20, raw={},
        )
    ])

    async with session_factory() as s:
        from app.models.corpus import CorpusItem
        from app.services.librarian import _librarian_for_subject

        librarian_agent = await _librarian_for_subject(s, subject_id)
        item = await s.get(CorpusItem, item_id)
        entry = await librarian.process_corpus_item(
            s, corpus_item=item, librarian=librarian_agent, chat_fn=chat
        )

    async with session_factory() as s:
        from app.models.corpus import CorpusItem
        item = await s.get(CorpusItem, item_id)
        assert item.summary == "Concise summary."
        assert item.tags_json == ["x", "y"]
        assert item.importance == 4
        assert entry.id is not None
        assert "First seen" in entry.comments


async def test_process_corpus_item_falls_back_on_bad_json(session_factory):
    subject_id, item_id = await _setup_with_item(session_factory)
    chat = _stub_chat([
        ChatResult(
            text="No JSON here, sorry.",
            prompt_tokens=50, completion_tokens=5, raw={},
        )
    ])

    async with session_factory() as s:
        from app.models.corpus import CorpusItem
        from app.services.librarian import _librarian_for_subject

        librarian_agent = await _librarian_for_subject(s, subject_id)
        item = await s.get(CorpusItem, item_id)
        await librarian.process_corpus_item(
            s, corpus_item=item, librarian=librarian_agent, chat_fn=chat,
        )

    async with session_factory() as s:
        from app.models.corpus import CorpusItem
        item = await s.get(CorpusItem, item_id)
        # Falls back to raw text + importance 3
        assert item.summary is not None
        assert item.importance == 3


async def test_process_new_for_subject_drains_pending(session_factory):
    subject_id, item_id = await _setup_with_item(session_factory)
    # Add another pending item so we have two
    async with session_factory() as s:
        await source_service.persist_new_items(
            s,
            subject_id=subject_id,
            source_id=None,
            items=[{
                "external_id": "ext-2", "title": "Another", "authors": [],
                "published_at": None, "url": None, "text": "Body 2",
            }],
        )

    chat = _stub_chat([
        ChatResult(text='{"summary":"s1","tags":["a"],"importance":2}', prompt_tokens=10, completion_tokens=5, raw={}),
        ChatResult(text='{"summary":"s2","tags":["b"],"importance":3}', prompt_tokens=10, completion_tokens=5, raw={}),
    ])

    async with session_factory() as s:
        entries = await librarian.process_new_for_subject(s, subject_id=subject_id, chat_fn=chat)

    assert len(entries) == 2
