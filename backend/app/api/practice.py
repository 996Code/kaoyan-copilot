"""专项练习：按科目/模块/年份抽题，即时判分（主观题留待 P2 LLM 批改）。"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_session
from app.models import AnswerRecord, Module, Question, Subject
from app.models.user import User

router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/questions")
def questions(
    subject: str,
    module: str,
    year: int | None = None,
    limit: int = 20,
    random: bool = True,
    session: Session = Depends(get_session),
):
    mod = session.scalar(
        select(Module)
        .join(Subject, Module.subject_id == Subject.id)
        .where(Subject.code == subject, Module.code == module)
    )
    if mod is None:
        raise HTTPException(status_code=404, detail="模块不存在")

    stmt = select(Question).where(Question.module_id == mod.id)
    if year:
        stmt = stmt.where(Question.year == year)
    stmt = stmt.order_by(func.random() if random else (Question.year.desc(), Question.number))
    stmt = stmt.limit(min(limit, 100))
    rows = session.scalars(stmt).all()

    out = []
    for q in rows:
        d = {
            "id": q.id,
            "number": q.number,
            "year": q.year,
            "qtype": q.qtype,
            "stem": q.stem,
            "stem_format": q.stem_format,
            "options": q.options,
            "score": float(q.score) if q.score is not None else None,
            "disputed": bool((q.raw or {}).get("answer_disputed")),
            "group_title": None,
            "group_material": None,
            "group_options": None,
            "group_image": None,
        }
        if q.group is not None:
            d["group_title"] = q.group.title
            d["group_material"] = q.group.material
            d["group_options"] = q.group.options
            d["group_image"] = q.group.material_image
        out.append(d)
    return out


class CheckIn(BaseModel):
    question_id: int
    answer: object  # 字母或文本


@router.post("/check")
def check(body: CheckIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    q = session.get(Question, body.question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="题目不存在")

    correct = None
    if q.qtype == "single_choice":
        correct = (
            body.answer is not None
            and str(body.answer).strip().upper() == str(q.answer).strip().upper()
        )
        # FSRS 联动：答对推进记忆，答错建卡+Again
        from app.core.srs import apply_question_answer

        apply_question_answer(session, user.id, q.id, correct)
        if correct is False:
            from app.api.wrongbook import record_wrong

            record_wrong(session, user.id, q.id)

    session.add(
        AnswerRecord(
            user_id=user.id,
            question_id=q.id,
            answer=body.answer,
            is_correct=correct,
            score=(float(q.score) if (correct and q.score is not None) else 0.0),
            source="practice",
        )
    )
    session.commit()

    return {
        "correct": correct,  # None = 主观题无法自动判定
        "correct_answer": q.answer if q.qtype == "single_choice" else None,
        "analysis": q.analysis,
        "disputed": bool((q.raw or {}).get("answer_disputed")),
    }
