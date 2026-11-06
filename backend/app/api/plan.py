"""40 天计划引擎：全部动态计算（FSRS 到期量 + 薄弱模块 + 词汇进度 + 模考建议）。

不做固定课表——每天打开看板时按最新学习状态实时生成今日任务，
这正是"根据学习情况灵活调整"的实现方式。
"""

from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.auth import current_user
from app.core.db import get_session
from app.models import (
    AnswerRecord, ExamRecord, Module, Paper, Question, ReviewCard, Subject, Word,
)
from app.models.user import User

router = APIRouter(prefix="/api/plan", tags=["plan"])


def _local_midnight_utc() -> datetime:
    now_local = datetime.now().astimezone()
    midnight_local = datetime.combine(now_local.date(), time.min, tzinfo=now_local.tzinfo)
    return midnight_local.astimezone(timezone.utc)


@router.get("/today")
def today(user: User = Depends(current_user), session: Session = Depends(get_session)):
    now = datetime.now(timezone.utc)
    exam_date = date.fromisoformat(settings.exam_date)
    days_left = (exam_date - datetime.now().astimezone().date()).days

    # --- 复习到期 ---
    due = {"wrong_question": 0, "word": 0}
    for ct in due:
        due[ct] = len(
            session.scalars(
                select(ReviewCard.id).where(ReviewCard.user_id == user.id, ReviewCard.card_type == ct, ReviewCard.due <= now)
            ).all()
        )
    total_cards = len(session.scalars(select(ReviewCard.id)).all())

    # --- 词汇进度 ---
    midnight = _local_midnight_utc()
    words_learned_total = len(
        session.scalars(select(ReviewCard.id).where(ReviewCard.user_id == user.id, ReviewCard.card_type == "word")).all()
    )
    words_learned_today = len(
        session.scalars(
            select(ReviewCard.id).where(
                ReviewCard.user_id == user.id, ReviewCard.card_type == "word", ReviewCard.created_at >= midnight
            )
        ).all()
    )
    words_total = len(session.scalars(select(Word.id)).all())

    # --- 薄弱模块（正确率最低优先） ---
    rows = session.execute(
        select(
            Module.code, Module.name, Subject.code, Subject.name,
            func.count(AnswerRecord.id),
            func.sum(func.cast(AnswerRecord.is_correct, __import__("sqlalchemy").Integer)),
        )
        .join(Question, AnswerRecord.question_id == Question.id)
        .join(Module, Question.module_id == Module.id)
        .join(Subject, Module.subject_id == Subject.id)
        .where(AnswerRecord.user_id == user.id, AnswerRecord.is_correct.is_not(None))
        .group_by(Module.code, Module.name, Subject.code, Subject.name)
    ).all()
    modules_acc = [
        {
            "subject_code": r[2], "subject_name": r[3],
            "module_code": r[0], "module_name": r[1],
            "attempts": r[4], "correct": int(r[5] or 0),
            "accuracy": round(int(r[5] or 0) / r[4] * 100) if r[4] else None,
        }
        for r in rows
    ]
    weak_modules = sorted(
        [m for m in modules_acc if m["attempts"] >= 3 and m["accuracy"] is not None],
        key=lambda m: m["accuracy"],
    )[:3]

    # --- 模考建议：各科最新一套未考过的真题，优先推荐考得少的一科 ---
    attempted = set(
        session.scalars(
            select(ExamRecord.paper_id).where(ExamRecord.user_id == user.id, ExamRecord.status == "submitted")
        ).all()
    )
    suggestions = []
    for sub_code in ("gz199", "en2"):
        papers = session.execute(
            select(Paper, Subject.code, Subject.id)
            .join(Subject, Paper.subject_id == Subject.id)
            .where(Subject.code == sub_code)
            .order_by(Paper.year.desc())
        ).all()
        exam_count = (
            session.execute(
                select(func.count(ExamRecord.id))
                .join(Paper, ExamRecord.paper_id == Paper.id)
                .where(Paper.subject_id == papers[0][2], ExamRecord.user_id == user.id, ExamRecord.status == "submitted")
            ).scalar_one()
            if papers
            else 0
        )
        for p, code, _sid in papers:
            if p.id not in attempted:
                suggestions.append(
                    {
                        "paper_id": p.id, "subject_code": code, "year": p.year,
                        "name": p.name, "exam_count": exam_count,
                    }
                )
                break
    mock = (
        min(suggestions, key=lambda s: s.pop("exam_count")) if suggestions else None
    )

    # --- 近 7 天正确率 ---
    week_ago = now - timedelta(days=7)
    recent = session.scalars(
        select(AnswerRecord).where(
            AnswerRecord.user_id == user.id, AnswerRecord.is_correct.is_not(None), AnswerRecord.created_at >= week_ago
        )
    ).all()
    by_day: dict[str, list[bool]] = {}
    for r in recent:
        d = r.created_at.astimezone().strftime("%m-%d")
        by_day.setdefault(d, []).append(bool(r.is_correct))
    recent_accuracy = [
        {"date": d, "accuracy": round(sum(v) / len(v) * 100), "attempts": len(v)}
        for d, v in sorted(by_day.items())
    ]

    # --- 今日模考/练习数 ---
    exams_today = len(
        session.scalars(
            select(ExamRecord.id).where(ExamRecord.user_id == user.id, ExamRecord.created_at >= midnight)
        ).all()
    )

    return {
        "today": datetime.now().astimezone().strftime("%Y-%m-%d %A"),
        "exam_date": settings.exam_date,
        "days_left": days_left,
        "due": due,
        "total_cards": total_cards,
        "words": {
            "daily_target": settings.words_per_day,
            "learned_today": words_learned_today,
            "remaining_today": max(0, settings.words_per_day - words_learned_today),
            "learned_total": words_learned_total,
            "total": words_total,
        },
        "weak_modules": weak_modules,
        "modules_accuracy": modules_acc,
        "mock_suggestion": mock,
        "recent_accuracy": recent_accuracy,
        "exams_today": exams_today,
    }
