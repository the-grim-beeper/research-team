async def test_login_succeeds_with_correct_credentials(client):
    r = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "pw"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and len(body["access_token"]) > 20


async def test_login_rejects_wrong_password(client):
    r = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "nope"})
    assert r.status_code == 401


async def test_me_returns_user_when_authenticated(client):
    login = await client.post("/api/v1/auth/login", json={"email": "admin@test.com", "password": "pw"})
    token = login.json()["access_token"]
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "admin@test.com"


async def test_me_rejects_missing_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401
