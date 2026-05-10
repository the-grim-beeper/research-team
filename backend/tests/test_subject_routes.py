async def _login(client) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "pw"})
    return r.json()["access_token"]


async def test_create_list_archive_flow(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/v1/subjects", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "AI governance", "brief": ""}
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    r = await client.get("/api/v1/subjects", headers=headers)
    assert [s["id"] for s in r.json()] == [sid]

    r = await client.post(f"/api/v1/subjects/{sid}/archive", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "archived"

    r = await client.get("/api/v1/subjects?status_filter=active", headers=headers)
    assert r.json() == []


async def test_three_active_limit_returns_409(client):
    token = await _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(3):
        r = await client.post(
            "/api/v1/subjects", headers=headers, json={"title": f"S{i}", "brief": ""}
        )
        assert r.status_code == 201
    r = await client.post(
        "/api/v1/subjects", headers=headers, json={"title": "S4", "brief": ""}
    )
    assert r.status_code == 409


async def test_subjects_require_auth(client):
    r = await client.get("/api/v1/subjects")
    assert r.status_code == 401
