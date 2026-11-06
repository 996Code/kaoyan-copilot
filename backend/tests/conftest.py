"""pytest 配置：使用独立的 kaoyan_test 库，每个会话重建表并灌入种子数据。

运行：cd backend && .venv/bin/python -m pytest tests -q
"""

import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://root:root@localhost:5432/kaoyan_test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

SEED = {"paper_id": None, "q_ids": [], "word_ids": []}


def _seed() -> None:
    from app.core.auth import register_user
    from app.core.db import SessionLocal
    from app.models import (
        Module, Paper, PaperQuestion, PaperSection, Question, Subject, Word,
    )

    with SessionLocal() as s:
        # 种子管理员（不依赖 login 时的空表自动建号，避免注册顺序影响）
        admin = register_user(s, "admin", "kaoyan2026")
        admin.is_admin = True
        sub = Subject(code="gz199", name="测试管综")
        s.add(sub)
        s.flush()
        math = Module(subject_id=sub.id, code="math", name="数学", sort=1)
        s.add(math)
        s.flush()
        paper = Paper(subject_id=sub.id, year=2099, name="测试卷", total_score=10, duration_minutes=30)
        s.add(paper)
        s.flush()
        sec = PaperSection(paper_id=paper.id, module_id=math.id, name="一、问题求解", sort=1)
        s.add(sec)
        s.flush()
        for i, ans in enumerate(["A", "B"], 1):
            q = Question(
                module_id=math.id, qtype="single_choice", number=i, stem=f"测试题 {i}",
                options=[{"key": k, "text": f"选项{k}"} for k in "ABCD"],
                answer=ans, score=3.0, year=2099,
            )
            s.add(q)
            s.flush()
            s.add(PaperQuestion(section_id=sec.id, question_id=q.id, sort=i))
        for rank, word in enumerate(["alpha", "beta"], 1):
            w = Word(headword=word, definition=f"{word} 释义", freq_rank=rank, source="TEST")
            s.add(w)
            s.flush()
            SEED["word_ids"].append(w.id)
        s.commit()
        SEED["paper_id"] = paper.id
        SEED["q_ids"] = [q.id for q in s.scalars(
            __import__("sqlalchemy").select(Question).where(Question.year == 2099)
        ).all()]


@pytest.fixture(scope="session", autouse=True)
def _database():
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    from app.models import Base  # noqa: F401
    import app.models  # noqa: F401 确保全部模型注册

    Base.metadata.create_all(engine)
    _seed()
    yield


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def seed():
    """种子数据（paper/题目/单词 id），避免测试从 conftest 导入造成双模块实例。"""
    return SEED


def make_user(client: TestClient, username: str, password: str = "pass1234") -> dict:
    """注册并返回 Authorization 头。"""
    res = client.post("/api/auth/register", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}
