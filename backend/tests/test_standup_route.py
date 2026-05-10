from unittest.mock import patch

from app.services.openrouter import ChatResult


async def _login(client) -> str:
    r = await client.post(
        "/api/v1/auth/login", json={"email": "admin@test.com", "password": "pw"}
    )
    return r.json()["access_token"]


async def test_standup_endpoint_returns_four_artifacts(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "T", "brief": ""}
    )
    sid = r.json()["id"]

    canned = ChatResult(text="X", prompt_tokens=10, completion_tokens=5, raw={})

    async def stub_chat(messages, *, model, max_tokens):
        return canned

    with patch("app.services.execution.openrouter.chat", new=stub_chat):
        r = await client.post(f"/api/v1/subjects/{sid}/standup", headers=headers)
    assert r.status_code == 200
    artifacts = r.json()
    assert len(artifacts) == 4
    kinds = [a["kind"] for a in artifacts]
    assert kinds == ["briefing", "critique", "roundtable_post", "open_question"]


async def test_user_can_post_artifact(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "T", "brief": ""}
    )
    sid = r.json()["id"]

    r = await client.post(
        f"/api/v1/subjects/{sid}/artifacts",
        headers=headers,
        json={
            "kind": "instruction",
            "title": "Fresh take?",
            "body_md": "Please push back on the briefing.",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["author_type"] == "user"
    assert body["body_md"].startswith("Please push back")


async def test_kind_filter(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "T", "brief": ""}
    )
    sid = r.json()["id"]

    await client.post(
        f"/api/v1/subjects/{sid}/artifacts",
        headers=headers,
        json={"kind": "instruction", "body_md": "do this"},
    )
    await client.post(
        f"/api/v1/subjects/{sid}/artifacts",
        headers=headers,
        json={"kind": "roundtable_post", "body_md": "thread"},
    )

    r = await client.get(
        f"/api/v1/subjects/{sid}/artifacts?kind=instruction", headers=headers
    )
    assert r.status_code == 200
    assert {a["kind"] for a in r.json()} == {"instruction"}
