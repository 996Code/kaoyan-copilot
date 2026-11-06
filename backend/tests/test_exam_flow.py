"""模考全流程测试：开考（答案不泄露）→ 保存 → 交卷判分 → 报告回看。"""

from tests.conftest import make_user


def test_full_exam_flow(client, seed):
    headers = make_user(client, "examer")

    # 开考
    res = client.post("/api/exams", json={"paper_id": seed["paper_id"]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    exam_id = data["exam"]["id"]
    assert data["exam"]["status"] == "in_progress"
    # 答题视图不得包含答案/解析
    questions = [
        q
        for s in data["paper"]["sections"]
        for b in s["blocks"]
        for q in (b["group"]["questions"] if b["kind"] == "group" else [b["question"]])
    ]
    assert len(questions) == 2
    assert all("answer" not in q and "analysis" not in q for q in questions)

    # 保存（断点续答）
    res = client.put(
        f"/api/exams/{exam_id}/answers",
        json={"answers": {str(seed["q_ids"][0]): "A"}},
        headers=headers,
    )
    assert res.status_code == 200

    # 交卷：q1 答 A（正确），q2 答 C（错误）→ 3/6
    res = client.post(
        f"/api/exams/{exam_id}/submit",
        json={"answers": {str(seed["q_ids"][0]): "A", str(seed["q_ids"][1]): "C"}},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["exam"]["status"] == "submitted"
    assert float(body["exam"]["objective_score"]) == 3.0
    assert float(body["exam"]["objective_total"]) == 6.0
    r1 = body["results"][str(seed["q_ids"][0])]
    r2 = body["results"][str(seed["q_ids"][1])]
    assert r1["is_correct"] is True and r2["is_correct"] is False

    # 报告回看（刷新后结果仍在，且带答案）
    res = client.get(f"/api/exams/{exam_id}", headers=headers)
    assert res.status_code == 200
    report = res.json()
    assert report["results"][str(seed["q_ids"][0])]["is_correct"] is True
    answers_in_report = [
        q
        for s in report["paper"]["sections"]
        for b in s["blocks"]
        for q in (b["group"]["questions"] if b["kind"] == "group" else [b["question"]])
    ]
    assert all("answer" in q for q in answers_in_report)

    # 其他人看不到这场考试
    other = make_user(client, "stranger")
    assert client.get(f"/api/exams/{exam_id}", headers=other).status_code == 404


def test_papers_listing(client, seed):
    headers = make_user(client, "browser")
    res = client.get("/api/papers?subject=gz199", headers=headers)
    assert res.status_code == 200
    papers = res.json()
    assert any(p["id"] == seed["paper_id"] for p in papers)
