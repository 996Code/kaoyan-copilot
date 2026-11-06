"""词汇学习：按词频顺序学新词（FSRS 首评），复习走 /api/review。按用户隔离。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_session
from app.core.srs import RATING_EASY, RATING_GOOD, RATING_HARD, review
from app.models.review import ReviewCard
from app.models.user import User
from app.models.word import Word

router = APIRouter(prefix="/api/vocab", tags=["vocab"])


@router.get("/learn_batch")
def learn_batch(
    count: int = 20,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    """取下一批未学词（按词频排名，高频优先）。"""
    learned_ids = set(
        session.scalars(
            select(ReviewCard.ref_id).where(
                ReviewCard.user_id == user.id, ReviewCard.card_type == "word"
            )
        ).all()
    )
    stmt = (
        select(Word)
        .where(~Word.id.in_(learned_ids) if learned_ids else True)
        .order_by(Word.freq_rank)
        .limit(min(count, 100))
    )
    words = session.scalars(stmt).all()
    total_words = len(session.scalars(select(Word.id)).all())
    return {
        "words": [
            {
                "id": w.id, "headword": w.headword, "phonetic": w.phonetic,
                "definition": w.definition, "tags": w.tags,
                "example": (w.examples or [{}])[0].get("sentence"),
                "example_translation": (w.examples or [{}])[0].get("translation"),
                "freq_rank": w.freq_rank,
            }
            for w in words
        ],
        "learned_total": len(learned_ids),
        "total": total_words,
    }


@router.get("/lookup")
def lookup(word: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """点词查义：词表精确匹配 → 简单词形还原（复数/ing/ed）。"""
    w = word.strip().lower()
    if not w:
        return {"found": False}
    from sqlalchemy import or_

    row = session.scalar(select(Word).where(Word.headword == w))
    if row is None:
        # 简易还原：-s/-es/-ing/-ed/-ied→y
        cands = []
        if w.endswith("ies"):
            cands.append(w[:-3] + "y")
        if w.endswith("es") and len(w) > 4:
            cands.append(w[:-2]); cands.append(w[:-1])
        if w.endswith("s") and not w.endswith("ss"):
            cands.append(w[:-1])
        if w.endswith("ing") and len(w) > 5:
            cands.append(w[:-3]); cands.append(w[:-3] + "e")
        if w.endswith("ed") and len(w) > 4:
            cands.append(w[:-1]); cands.append(w[:-2]); cands.append(w[:-2] + "y" if w.endswith("ied") else w[:-2])
        for c in cands:
            row = session.scalar(select(Word).where(Word.headword == c))
            if row:
                break
    if row is None:
        return {"found": False}
    learned = session.scalar(
        select(ReviewCard.id).where(
            ReviewCard.user_id == user.id, ReviewCard.card_type == "word", ReviewCard.ref_id == row.id
        )
    )
    return {
        "found": True, "word_id": row.id, "headword": row.headword,
        "definition": row.definition, "freq_rank": row.freq_rank,
        "learned": learned is not None,
    }


class LearnOneIn(BaseModel):
    word_id: int
    familiarity: str  # hard / good / easy（生 / 模糊 / 熟）


@router.post("/learn")
def learn_one(body: LearnOneIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    mapping = {"hard": RATING_HARD, "good": RATING_GOOD, "easy": RATING_EASY}
    rating = mapping.get(body.familiarity)
    if rating is None:
        raise HTTPException(status_code=400, detail="familiarity 取 hard/good/easy")
    row = review(session, user.id, "word", body.word_id, rating, "learn", create_if_missing=True)
    session.commit()
    return {"word_id": body.word_id, "card_id": row.id, "new_due": row.due}
