"""核心：双用户数据隔离（练习/错题本/复习卡/词汇/看板）。"""

from tests.conftest import make_user


def test_practice_wrong_answer_isolation(client, seed):
    alice = make_user(client, "iso_alice")
    bob = make_user(client, "iso_bob")

    # alice 答错一道练习题
    res = client.post(
        "/api/practice/check",
        json={"question_id": seed["q_ids"][1], "answer": "D"},  # 正确答案 B
        headers=alice,
    )
    assert res.status_code == 200 and res.json()["correct"] is False

    # 错题本：alice 1 条，bob 0 条
    assert len(client.get("/api/wrongbook?subject=gz199", headers=alice).json()) == 1
    assert len(client.get("/api/wrongbook?subject=gz199", headers=bob).json()) == 0

    # 复习卡：alice 有卡（未到期也计入 total），bob 无
    a_stats = client.get("/api/review/stats", headers=alice).json()
    b_stats = client.get("/api/review/stats", headers=bob).json()
    assert a_stats["total"]["wrong_question"] == 1
    assert b_stats["total"]["wrong_question"] == 0


def test_vocab_isolation(client):
    alice = make_user(client, "voc_alice")
    bob = make_user(client, "voc_bob")

    batch = client.get("/api/vocab/learn_batch?count=10", headers=alice).json()
    assert batch["learned_total"] == 0 and len(batch["words"]) == 2

    # alice 学第一个词
    res = client.post(
        "/api/vocab/learn",
        json={"word_id": batch["words"][0]["id"], "familiarity": "good"},
        headers=alice,
    )
    assert res.status_code == 200

    # alice 的下一批不再含该词；bob 的批次不受影响（仍从第一个词开始）
    a_batch = client.get("/api/vocab/learn_batch?count=10", headers=alice).json()
    assert a_batch["learned_total"] == 1
    assert all(w["id"] != batch["words"][0]["id"] for w in a_batch["words"])
    b_batch = client.get("/api/vocab/learn_batch?count=10", headers=bob).json()
    assert b_batch["learned_total"] == 0
    assert any(w["id"] == batch["words"][0]["id"] for w in b_batch["words"])


def test_plan_isolation(client, seed):
    alice = make_user(client, "plan_alice")
    bob = make_user(client, "plan_bob")

    # alice 做对一道 → bob 的看板不应出现 alice 的作答
    client.post(
        "/api/practice/check",
        json={"question_id": seed["q_ids"][0], "answer": "A"},
        headers=alice,
    )
    a_plan = client.get("/api/plan/today", headers=alice).json()
    b_plan = client.get("/api/plan/today", headers=bob).json()
    assert sum(m["attempts"] for m in a_plan["modules_accuracy"]) == 1
    assert sum(m["attempts"] for m in b_plan["modules_accuracy"]) == 0
    assert b_plan["words"]["learned_total"] == 0
