async def _login(client) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "pw"})
    return r.json()["access_token"]


async def test_roles_endpoint_returns_eight(client):
    token = await _login(client)
    r = await client.get("/api/v1/roles", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 8


async def test_subject_create_then_list_agents(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "Topic", "brief": ""}
    )
    sid = r.json()["id"]

    r = await client.get(f"/api/v1/subjects/{sid}/agents", headers=headers)
    assert r.status_code == 200
    agents = r.json()
    assert len(agents) == 8

    by_slug = {a["role"]["slug"] for a in agents}
    assert by_slug == {
        "librarian", "editor", "critic", "contrarian", "question_generator",
        "empiricist", "theorist", "historian",
    }


async def test_get_subject_endpoint(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "X", "brief": "Y"}
    )
    sid = r.json()["id"]

    r = await client.get(f"/api/v1/subjects/{sid}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "X" and body["brief"] == "Y"


async def test_patch_agent(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "Topic", "brief": ""}
    )
    sid = r.json()["id"]
    r = await client.get(f"/api/v1/subjects/{sid}/agents", headers=headers)
    aid = r.json()[0]["id"]

    r = await client.patch(
        f"/api/v1/agents/{aid}",
        headers=headers,
        json={"model": "openai/gpt-4o-mini", "cycle": "hourly", "daily_budget_usd": "0.50"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["model"] == "openai/gpt-4o-mini"
    assert body["cycle"] == "hourly"
    assert float(body["daily_budget_usd"]) == 0.5


async def test_patch_agent_rejects_invalid_cycle(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "Topic", "brief": ""}
    )
    sid = r.json()["id"]
    r = await client.get(f"/api/v1/subjects/{sid}/agents", headers=headers)
    aid = r.json()[0]["id"]

    r = await client.patch(
        f"/api/v1/agents/{aid}", headers=headers, json={"cycle": "weekly"}
    )
    assert r.status_code == 422
