"""复习中心：混合卡片队列（错题卡 + 单词卡）与作答。按用户隔离。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_session
from app.core.srs import (
    RATING_AGAIN, RATING_EASY, RATING_GOOD, RATING_HARD,
    review,
)
from app.models import Question, ReviewCard
from app.models.user import User
from app.models.word import Word

router = APIRouter(prefix="/api/review", tags=["review"])


def _card_payload(session: Session, row: ReviewCard) -> dict:
    base = {
        "card_id": row.id,
        "card_type": row.card_type,
        "due": row.due,
        "state": row.state,
        "reps": row.reps,
        "lapses": row.lapses,
    }
    if row.card_type == "wrong_question":
        q = session.get(Question, row.ref_id)
        if q is None:
            return {**base, "missing": True}
        return {
            **base,
            "question": {
                "id": q.id, "number": q.number, "year": q.year, "qtype": q.qtype,
                "stem": q.stem, "options": q.options,
                "analysis": q.analysis, "disputed": bool((q.raw or {}).get("answer_disputed")),
                "group_title": q.group.title if q.group else None,
                "group_material": q.group.material if q.group else None,
                "group_options": q.group.options if q.group else None,
                "group_image": q.group.material_image if q.group else None,
            },
        }
    w = session.get(Word, row.ref_id)
    if w is None:
        return {**base, "missing": True}
    ex = (w.examples or [{}])[0]
    return {
        **base,
        "word": {
            "id": w.id, "headword": w.headword, "phonetic": w.phonetic,
            "definition": w.definition, "example": ex.get("sentence"),
            "example_translation": ex.get("translation"),
        },
    }


def _scoped(session: Session, user_id: int):
    return select(ReviewCard).where(ReviewCard.user_id == user_id)


@router.get("/queue")
def queue(
    limit: int = 30,
    card_type: str | None = None,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    now = datetime.now(timezone.utc)
    stmt = _scoped(session, user.id).where(ReviewCard.due <= now)
    if card_type:
        stmt = stmt.where(ReviewCard.card_type == card_type)
    stmt = stmt.order_by(ReviewCard.due).limit(min(limit, 100))
    rows = session.scalars(stmt).all()
    payloads = [_card_payload(session, r) for r in rows]

    due_counts = {"wrong_question": 0, "word": 0}
    for ct in due_counts:
        due_counts[ct] = len(
            session.scalars(
                _scoped(session, user.id).where(
                    ReviewCard.due <= now, ReviewCard.card_type == ct
                )
            ).all()
        )
    return {
        "cards": [p for p in payloads if not p.get("missing")],
        "due_counts": due_counts,
    }


@router.get("/stats")
def stats(user: User = Depends(current_user), session: Session = Depends(get_session)):
    now = datetime.now(timezone.utc)
    total = {"wrong_question": 0, "word": 0}
    due = {"wrong_question": 0, "word": 0}
    for ct in total:
        total[ct] = len(
            session.scalars(_scoped(session, user.id).where(ReviewCard.card_type == ct)).all()
        )
        due[ct] = len(
            session.scalars(
                _scoped(session, user.id).where(
                    ReviewCard.card_type == ct, ReviewCard.due <= now
                )
            ).all()
        )
    return {"total": total, "due": due}


class AnswerIn(BaseModel):
    card_id: int
    rating: int  # 1-4
    source: str = "manual"


@router.post("/answer")
def answer(body: AnswerIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    if body.rating not in (RATING_AGAIN, RATING_HARD, RATING_GOOD, RATING_EASY):
        raise HTTPException(status_code=400, detail="rating 取值 1-4")
    row = session.get(ReviewCard, body.card_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="卡片不存在")
    review(session, user.id, row.card_type, row.ref_id, body.rating, body.source)
    session.commit()
    session.refresh(row)
    return {"card_id": row.id, "new_due": row.due, "state": row.state}


class AnswerQuestionIn(BaseModel):
    card_id: int
    answer: object


@router.post("/answer_question")
def answer_question(
    body: AnswerQuestionIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    """错题卡复习：作答自动判分并映射评分（对=Good，错=Again）。"""
    row = session.get(ReviewCard, body.card_id)
    if row is None or row.user_id != user.id or row.card_type != "wrong_question":
        raise HTTPException(status_code=404, detail="错题卡不存在")
    q = session.get(Question, row.ref_id)
    correct = (
        body.answer is not None
        and str(body.answer).strip().upper() == str(q.answer).strip().upper()
    )
    review(session, user.id, "wrong_question", row.ref_id, RATING_GOOD if correct else RATING_AGAIN, "manual")
    session.commit()
    session.refresh(row)
    return {
        "correct": correct,
        "correct_answer": q.answer,
        "analysis": q.analysis,
        "new_due": row.due,
    }
