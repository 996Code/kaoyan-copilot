"""系统管理（仅 admin）：用户管理、LLM 配置、系统统计。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.auth import hash_password, require_admin
from app.core.db import get_session
from app.core.llm import chat_complete, llm_ready
from app.core.settings_store import LLM_KEYS, get_llm_config, mask_key, set_many
from app.models import (
    AiCache, AnswerRecord, ExamRecord, Paper, Question, ReviewCard, ReviewLog, Subject,
    WrongItem,
)
from app.models.user import User
from app.models.word import Word

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------- 用户管理 ----------

@router.get("/users")
def list_users(session: Session = Depends(get_session)):
    users = session.scalars(select(User).order_by(User.id)).all()
    out = []
    for u in users:
        exams = session.scalar(
            select(func.count(ExamRecord.id)).where(
                ExamRecord.user_id == u.id, ExamRecord.status == "submitted"
            )
        )
        ans = session.execute(
            select(func.count(), func.sum(func.cast(AnswerRecord.is_correct, __import__("sqlalchemy").Integer)))
            .where(AnswerRecord.user_id == u.id, AnswerRecord.is_correct.is_not(None))
        ).one()
        answers, correct = int(ans[0]), int(ans[1] or 0)
        wrong_active = session.scalar(
            select(func.count(WrongItem.id)).where(
                WrongItem.user_id == u.id, WrongItem.mastered.is_(False)
            )
        )
        cards = session.scalar(
            select(func.count(ReviewCard.id)).where(ReviewCard.user_id == u.id)
        )
        words = session.scalar(
            select(func.count(ReviewCard.id)).where(
                ReviewCard.user_id == u.id, ReviewCard.card_type == "word"
            )
        )
        last_exam = session.scalar(
            select(func.max(ExamRecord.started_at)).where(ExamRecord.user_id == u.id)
        )
        last_answer = session.scalar(
            select(func.max(AnswerRecord.created_at)).where(AnswerRecord.user_id == u.id)
        )
        last_active = max(filter(None, [last_exam, last_answer]), default=None)
        out.append(
            {
                "id": u.id,
                "username": u.username,
                "is_admin": bool(u.is_admin),
                "created_at": u.created_at,
                "exams": exams,
                "answers": answers,
                "accuracy": round(correct / answers * 100) if answers else None,
                "wrong_active": wrong_active,
                "cards": cards,
                "words_learned": words,
                "last_active": last_active,
            }
        )
    return out


class ResetPasswordIn(BaseModel):
    password: str = Field(min_length=4, max_length=64)


@router.post("/users/{user_id}/reset_password")
def reset_password(user_id: int, body: ResetPasswordIn, session: Session = Depends(get_session)):
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.password_hash = hash_password(body.password)
    session.commit()
    return {"ok": True, "username": u.username}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(require_admin), session: Session = Depends(get_session)):
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.is_admin:
        raise HTTPException(status_code=400, detail="不能删除管理员账号")
    # 级联清理该用户全部数据（题目/试卷等全局数据不动）
    card_ids = select(ReviewCard.id).where(ReviewCard.user_id == user_id)
    session.execute(delete(ReviewLog).where(ReviewLog.card_id.in_(card_ids)))
    session.execute(delete(ReviewCard).where(ReviewCard.user_id == user_id))
    session.execute(delete(WrongItem).where(WrongItem.user_id == user_id))
    session.execute(delete(AnswerRecord).where(AnswerRecord.user_id == user_id))
    session.execute(delete(ExamRecord).where(ExamRecord.user_id == user_id))
    session.delete(u)
    session.commit()
    return {"ok": True, "deleted": u.username}


# ---------- LLM 配置 ----------

@router.get("/settings")
def get_settings(session: Session = Depends(get_session)):
    cfg = get_llm_config(session)
    return {
        "llm_base_url": cfg["llm_base_url"],
        "llm_model": cfg["llm_model"],
        "llm_api_key_masked": mask_key(cfg["llm_api_key"]),
        "llm_ready": llm_ready(cfg),
    }


class SettingsIn(BaseModel):
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""  # 留空表示保持不变


@router.put("/settings")
def put_settings(body: SettingsIn, session: Session = Depends(get_session)):
    values = {"llm_base_url": body.llm_base_url.strip(), "llm_model": body.llm_model.strip()}
    if body.llm_api_key.strip():
        values["llm_api_key"] = body.llm_api_key.strip()
    set_many(session, values)
    return get_settings(session)


@router.post("/settings/test")
async def test_llm(session: Session = Depends(get_session)):
    import time

    cfg = get_llm_config(session)
    if not llm_ready(cfg):
        return {"ok": False, "error": "配置不完整（base_url / api_key / model 缺一不可）"}
    t0 = time.time()
    try:
        reply = await chat_complete(
            [{"role": "user", "content": "回复两个字：收到"}], cfg, temperature=0, timeout=20
        )
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "latency_ms": int((time.time() - t0) * 1000), "reply": (reply or "").strip()[:50]}


# ---------- 系统统计 ----------

@router.get("/stats")
def system_stats(session: Session = Depends(get_session)):
    def count(stmt):
        return session.scalar(select(func.count()).select_from(stmt))

    return {
        "users": count(User),
        "subjects": count(Subject),
        "papers": count(Paper),
        "questions": count(Question),
        "words": count(Word),
        "exams_submitted": session.scalar(
            select(func.count(ExamRecord.id)).where(ExamRecord.status == "submitted")
        ),
        "answers": count(AnswerRecord),
        "review_cards": count(ReviewCard),
        "ai_cache": count(AiCache),
        "llm_ready": llm_ready(get_llm_config(session)),
    }
