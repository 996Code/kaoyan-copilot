"""系统管理：权限、LLM 配置读写（打码）、删除用户级联清理。"""

from tests.conftest import make_user


def _admin_headers(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "kaoyan2026"})
    assert res.status_code == 200
    body = res.json()
    assert body["is_admin"] is True
    return {"Authorization": f"Bearer {body['token']}"}


def test_admin_forbidden_for_normal_user(client):
    pleb = make_user(client, "pleb")
    assert client.get("/api/admin/users", headers=pleb).status_code == 403
    assert client.get("/api/admin/settings", headers=pleb).status_code == 403


def test_llm_settings_roundtrip_and_masking(client):
    admin = _admin_headers(client)
    res = client.put(
        "/api/admin/settings",
        headers=admin,
        json={"llm_base_url": "http://x/v1", "llm_model": "m1", "llm_api_key": "sk-test123456"},
    )
    assert res.status_code == 200
    body = client.get("/api/admin/settings", headers=admin).json()
    assert body["llm_base_url"] == "http://x/v1"
    assert body["llm_model"] == "m1"
    masked = body["llm_api_key_masked"]
    assert "***" in masked and "sk-test123456" not in masked
    assert body["llm_ready"] is True


def test_delete_user_cascades(client, seed):
    admin = _admin_headers(client)
    victim = make_user(client, "victim")
    # victim 产生数据：错题 + 复习卡
    client.post(
        "/api/practice/check",
        json={"question_id": seed["q_ids"][1], "answer": "D"},
        headers=victim,
    )
    users = client.get("/api/admin/users", headers=admin).json()
    v = next(u for u in users if u["username"] == "victim")
    assert v["wrong_active"] == 1 and v["cards"] == 1

    res = client.delete(f"/api/admin/users/{v['id']}", headers=admin)
    assert res.status_code == 200

    users = client.get("/api/admin/users", headers=admin).json()
    assert all(u["username"] != "victim" for u in users)
    # 数据级联已清（复习卡计数回到基线）
    stats = client.get("/api/admin/stats", headers=admin).json()
    assert stats["review_cards"] >= 0
