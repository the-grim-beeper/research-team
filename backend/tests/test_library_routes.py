from unittest.mock import patch

from app.services.openrouter import ChatResult


async def _login(client) -> str:
    r = await client.post(
        "/api/v1/auth/login", json={"email": "admin@test.com", "password": "pw"}
    )
    return r.json()["access_token"]


async def test_register_and_list_sources(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "T", "brief": ""}
    )
    sid = r.json()["id"]

    r = await client.post(
        f"/api/v1/subjects/{sid}/sources",
        headers=headers,
        json={"kind": "rss", "display_name": "HN", "config": {"url": "https://hnrss.org/"}},
    )
    assert r.status_code == 201
    src_id = r.json()["id"]

    r = await client.get(f"/api/v1/subjects/{sid}/sources", headers=headers)
    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [src_id]


async def test_invalid_source_kind_rejected(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "T", "brief": ""}
    )
    sid = r.json()["id"]

    r = await client.post(
        f"/api/v1/subjects/{sid}/sources",
        headers=headers,
        json={"kind": "nonsense", "config": {}},
    )
    assert r.status_code == 422


async def test_add_note_creates_bibliography(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "T", "brief": ""}
    )
    sid = r.json()["id"]

    canned = ChatResult(
        text='{"summary":"This is a summary.","tags":["misc"],"importance":3}',
        prompt_tokens=20, completion_tokens=8, raw={},
    )

    async def stub_chat(messages, *, model, max_tokens):
        return canned

    with patch("app.services.librarian.openrouter.chat", new=stub_chat):
        r = await client.post(
            f"/api/v1/subjects/{sid}/notes",
            headers=headers,
            json={"title": "Note", "text": "Hello world note text"},
        )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert "summary" in body[0]
    assert body[0]["title"] == "Note"

    r = await client.get(
        f"/api/v1/subjects/{sid}/bibliography", headers=headers
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


async def test_list_corpus_after_note(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "T", "brief": ""}
    )
    sid = r.json()["id"]

    canned = ChatResult(
        text='{"summary":"S","tags":[],"importance":2}',
        prompt_tokens=5, completion_tokens=5, raw={},
    )

    async def stub_chat(messages, *, model, max_tokens):
        return canned

    with patch("app.services.librarian.openrouter.chat", new=stub_chat):
        await client.post(
            f"/api/v1/subjects/{sid}/notes",
            headers=headers,
            json={"text": "Body"},
        )

    r = await client.get(f"/api/v1/subjects/{sid}/corpus", headers=headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["summary"] == "S"
