"""错题本：答错自动归集（考试+练习），支持「已消灭」标记。按用户隔离。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_session
from app.models import AnswerRecord, Module, Question, Subject, WrongItem
from app.models.user import User

router = APIRouter(prefix="/api/wrongbook", tags=["wrongbook"])


def record_wrong(session: Session, user_id: int, question_id: int) -> None:
    """答错入本：计数 +1、重新激活（再次答错时撤销已消灭）。"""
    item = session.scalar(
        select(WrongItem).where(WrongItem.user_id == user_id, WrongItem.question_id == question_id)
    )
    if item is None:
        session.add(WrongItem(user_id=user_id, question_id=question_id, wrong_count=1))
    else:
        item.wrong_count += 1
        item.mastered = False
        item.last_wrong_at = datetime.now(timezone.utc)


def _last_wrong_answer(session: Session, user_id: int, question_id: int):
    return session.scalar(
        select(AnswerRecord)
        .where(
            AnswerRecord.user_id == user_id,
            AnswerRecord.question_id == question_id,
            AnswerRecord.is_correct.is_(False),
        )
        .order_by(AnswerRecord.id.desc())
        .limit(1)
    )


@router.get("")
def list_wrong(
    subject: str,
    module: str | None = None,
    mastered: bool = False,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    stmt = (
        select(WrongItem, Question, Module, Subject)
        .join(Question, WrongItem.question_id == Question.id)
        .join(Module, Question.module_id == Module.id)
        .join(Subject, Module.subject_id == Subject.id)
        .where(Subject.code == subject, WrongItem.user_id == user.id, WrongItem.mastered == mastered)
        .order_by(WrongItem.last_wrong_at.desc())
        .limit(300)
    )
    if module:
        stmt = stmt.where(Module.code == module)

    out = []
    for item, q, mod, _sub in session.execute(stmt).all():
        last = _last_wrong_answer(session, user.id, q.id)
        out.append(
            {
                "question": {
                    "id": q.id,
                    "number": q.number,
                    "year": q.year,
                    "qtype": q.qtype,
                    "stem": q.stem,
                    "options": q.options,
                    "answer": q.answer if q.qtype == "single_choice" else None,
                    "analysis": q.analysis,
                    "disputed": bool((q.raw or {}).get("answer_disputed")),
                    "group_title": q.group.title if q.group else None,
                    "group_material": q.group.material if q.group else None,
                    "group_options": q.group.options if q.group else None,
                    "group_image": q.group.material_image if q.group else None,
                },
                "module": {"code": mod.code, "name": mod.name},
                "wrong_count": item.wrong_count,
                "mastered": item.mastered,
                "last_wrong_at": item.last_wrong_at,
                "last_answer": last.answer if last else None,
            }
        )
    return out


class MasterIn(BaseModel):
    mastered: bool


@router.post("/{question_id}/master")
def set_mastered(
    question_id: int,
    body: MasterIn,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    item = session.scalar(
        select(WrongItem).where(WrongItem.user_id == user.id, WrongItem.question_id == question_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="该题不在错题本中")
    item.mastered = body.mastered
    session.commit()
    return {"question_id": question_id, "mastered": item.mastered}


@router.get("/stats")
def stats(subject: str, user: User = Depends(current_user), session: Session = Depends(get_session)):
    rows = session.execute(
        select(Module.code, WrongItem.mastered, func.count(WrongItem.id))
        .join(Question, WrongItem.question_id == Question.id)
        .join(Module, Question.module_id == Module.id)
        .join(Subject, Module.subject_id == Subject.id)
        .where(Subject.code == subject, WrongItem.user_id == user.id)
        .group_by(Module.code, WrongItem.mastered)
    ).all()
    by_module: dict[str, dict] = {}
    for code, mastered, cnt in rows:
        m = by_module.setdefault(code, {"active": 0, "mastered": 0})
        m["mastered" if mastered else "active"] = cnt
    return by_module
