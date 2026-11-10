"""知识速成卡：分类总览、学卡（首评入 FSRS）、到期复习走 /api/review。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_session
from app.core.srs import review
from app.models.knowledge import KnowledgeCard
from app.models.review import ReviewCard
from app.models.user import User

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/overview")
def overview(user: User = Depends(current_user), session: Session = Depends(get_session)):
    now = datetime.now(timezone.utc)
    rows = session.execute(
        select(
            KnowledgeCard.subject_code, KnowledgeCard.module_name, KnowledgeCard.category,
            func.count(KnowledgeCard.id),
        )
        .group_by(KnowledgeCard.subject_code, KnowledgeCard.module_name, KnowledgeCard.category)
        .order_by(KnowledgeCard.subject_code, KnowledgeCard.module_name, func.min(KnowledgeCard.sort))
    ).all()

    learned_ids = set(
        session.scalars(
            select(ReviewCard.ref_id).where(
                ReviewCard.user_id == user.id, ReviewCard.card_type == "knowledge"
            )
        ).all()
    )
    due_ids = set(
        session.scalars(
            select(ReviewCard.ref_id).where(
                ReviewCard.user_id == user.id,
                ReviewCard.card_type == "knowledge",
                ReviewCard.due <= now,
            )
        ).all()
    )
    # 一次拉全量卡片 id 按分类分组，替代逐分类循环查询（N+1）
    ids_by_cat: dict = {}
    for cid, sub, mod, cat in session.execute(
        select(KnowledgeCard.id, KnowledgeCard.subject_code, KnowledgeCard.module_name, KnowledgeCard.category)
    ).all():
        ids_by_cat.setdefault((sub, mod, cat), []).append(cid)

    out = []
    for sub, mod, cat, total in rows:
        ids = ids_by_cat.get((sub, mod, cat), [])
        n_learned = len(learned_ids & set(ids))
        n_due = len(due_ids & set(ids))
        out.append({
            "subject_code": sub, "module_name": mod, "category": cat,
            "total": total, "learned": n_learned, "due": n_due,
        })
    return out


@router.get("/states")
def states(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """全量知识卡 + 当前用户学习状态，按 "subject|category" 分组。"""
    learned_ids = set(
        session.scalars(
            select(ReviewCard.ref_id).where(
                ReviewCard.user_id == user.id, ReviewCard.card_type == "knowledge"
            )
        ).all()
    )
    cards = session.scalars(select(KnowledgeCard).order_by(KnowledgeCard.sort)).all()
    out: dict = {}
    for c in cards:
        key = f"{c.subject_code}|{c.category}"
        out.setdefault(key, []).append({
            "id": c.id, "title": c.title, "back": c.back,
            "module_name": c.module_name, "learned": c.id in learned_ids,
        })
    return out


class LearnIn(BaseModel):
    card_id: int
    familiarity: int  # 1 不认识(Again) 2 模糊(Hard) 3 认识(Good)


@router.post("/learn")
def learn(body: LearnIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if body.familiarity not in (1, 2, 3):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="familiarity 取 1/2/3")
    card = session.get(KnowledgeCard, body.card_id)
    if card is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="卡片不存在")
    row = review(session, user.id, "knowledge", card.id, body.familiarity, "learn", create_if_missing=True)
    session.commit()
    return {"card_id": card.id, "new_due": row.due}
