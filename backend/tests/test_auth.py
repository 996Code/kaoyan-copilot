"""认证与用户体系测试。"""


def test_register_and_login(client):
    res = client.post("/api/auth/register", json={"username": "alice", "password": "pass1234"})
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "alice" and body["token"]

    res = client.post("/api/auth/login", json={"username": "alice", "password": "pass1234"})
    assert res.status_code == 200 and res.json()["token"]


def test_register_duplicate(client):
    client.post("/api/auth/register", json={"username": "bob", "password": "pass1234"})
    res = client.post("/api/auth/register", json={"username": "bob", "password": "other567"})
    assert res.status_code == 409


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"username": "carol", "password": "pass1234"})
    res = client.post("/api/auth/login", json={"username": "carol", "password": "wrong!"})
    assert res.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_api_requires_auth(client):
    assert client.get("/api/subjects").status_code == 401
    assert client.get("/api/papers?subject=gz199").status_code == 401
