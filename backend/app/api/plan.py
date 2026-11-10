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

GOALS = {"gz199": 120.0, "en2": 55.0}  # 国家线目标
FULL = {"gz199": 200.0, "en2": 100.0}


def _estimate_scores(session, user_id: int) -> dict[str, list[dict]]:
    """按科目汇总每次已交卷模考的估分（客观 + 主观 AI 批改，未批主观按历史主观率估）。"""
    from app.models import AnswerRecord

    recs = session.execute(
        select(ExamRecord, Subject.code, Paper.year)
        .join(Paper, ExamRecord.paper_id == Paper.id)
        .join(Subject, Paper.subject_id == Subject.id)
        .where(ExamRecord.user_id == user_id, ExamRecord.status == "submitted")
        .order_by(ExamRecord.submitted_at)
    ).all()
    by_sub: dict[str, list[dict]] = {}
    for rec, sub_code, year in recs:
        rows = session.scalars(
            select(AnswerRecord).where(AnswerRecord.exam_id == rec.id)
        ).all()
        obj = sub_graded = sub_full = 0.0
        for r in rows:
            q = r.question
            if q is None:
                continue
            score = float(r.score or 0)
            if q.qtype == "single_choice":
                obj += score
            else:
                sub_graded += score if r.score is not None else 0.0
                sub_full += float(q.score or 0)
                # AI 批改过（is_correct 为 None 且 score 有值）的按已批算
        est = obj + sub_graded
        by_sub.setdefault(sub_code, []).append({
            "exam_id": rec.id, "year": year,
            "objective": round(obj, 1), "subjective": round(sub_graded, 1),
            "estimate": round(est, 1),
            "date": rec.submitted_at.strftime("%m-%d") if rec.submitted_at else None,
        })
    return by_sub


def _forecast(series: list[float], days_left: int, goal: float, full: float):
    """线性趋势外推 + 正态达标概率。样本不足时给保守估计。"""
    n = len(series)
    if n == 0:
        return None
    mean = sum(series) / n
    if n >= 3 and days_left > 0:
        # 最小二乘斜率（按次序）
        xs = list(range(n))
        mx = sum(xs) / n
        slope = sum((x - mx) * (y - mean) for x, y in zip(xs, series)) / sum((x - mx) ** 2 for x in xs)
        pace = slope * min(days_left / 7.0, 6)  # 每次模考间隔近似一周，封顶 6 次增量
        pred = mean + max(0, pace)
    else:
        pred = mean
    pred = min(pred, full)
    sigma = (sum((y - mean) ** 2 for y in series) / n) ** 0.5 if n >= 2 else full * 0.12
    sigma = max(sigma, full * 0.05)
    import math

    z = (pred - goal) / sigma
    prob = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return {
        "mean": round(mean, 1), "predicted": round(pred, 1), "goal": goal,
        "gap": round(pred - goal, 1), "probability": round(prob * 100),
    }


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
    total_cards = len(
        session.scalars(select(ReviewCard.id).where(ReviewCard.user_id == user.id)).all()
    )

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
        # 学习打卡：今天有作答 + 连续天数
        "streak": _study_streak(session, user.id),
    }


def _study_streak(session, user_id: int) -> dict:
    """学习打卡：今天是否已作答 + 连续学习天数。"""
    from datetime import timedelta

    all_dates = set(
        r.strftime("%Y-%m-%d")
        for r in session.scalars(
            select(AnswerRecord.created_at).where(AnswerRecord.user_id == user_id)
        ).all()
    )
    today_str = datetime.now().astimezone().strftime("%Y-%m-%d")
    studied_today = today_str in all_dates
    # 从今天（或昨天）往前数连续天数
    streak = 0
    check = datetime.now().astimezone()
    if not studied_today:
        check -= timedelta(days=1)
    while check.strftime("%Y-%m-%d") in all_dates:
        streak += 1
        check -= timedelta(days=1)
    return {"studied_today": studied_today, "streak_days": streak}


@router.get("/calendar")
def calendar(user=Depends(current_user), session: Session = Depends(get_session)):
    """40 天冲刺日历：考试日倒排的学习阶段 + 每日完成情况。"""
    from datetime import date as DateType, timedelta

    exam_date = DateType.fromisoformat(settings.exam_date)
    today = datetime.now().astimezone().date()
    days_left = (exam_date - today).days

    # 已学日期（有作答记录）
    studied_dates = set(
        r.strftime("%Y-%m-%d")
        for r in session.scalars(
            select(AnswerRecord.created_at).where(AnswerRecord.user_id == user.id)
        ).all()
    )
    # 已模考日期
    exam_dates = set(
        r.strftime("%Y-%m-%d")
        for r in session.scalars(
            select(ExamRecord.created_at).where(
                ExamRecord.user_id == user.id, ExamRecord.status == "submitted"
            )
        ).all()
    )

    # 学习阶段（距考试）
    phases = [
        (25, "冲刺期", "刷真题+错题重做"),
        (12, "真题模考期", "隔天一套限时模考+复盘"),
        (5, "考前调整期", "只看错题+知识卡，不做新题"),
        (0, "考试周", "背模板+调整作息"),
    ]

    days = []
    for i in range(min(42, days_left + 1)):
        d = today + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        phase = next((p[1] for p in phases if days_left - i > p[0] and p[0] > 0 or (days_left - i <= p[0] and p[0] == 0)), phases[0][1])
        # 简化阶段计算
        dl = days_left - i
        if dl > 25: phase_name = "基础冲刺"
        elif dl > 12: phase_name = "真题模考"
        elif dl > 5: phase_name = "考前调整"
        else: phase_name = "考试周"
        days.append({
            "date": d_str,
            "days_to_exam": dl,
            "is_today": d == today,
            "is_past": d < today,
            "is_exam_day": dl == 0,
            "studied": d_str in studied_dates,
            "exam_taken": d_str in exam_dates,
            "phase": phase_name,
        })

    return {"exam_date": settings.exam_date, "days_left": days_left, "days": days}


@router.get("/trends")
def trends(user=Depends(current_user), session: Session = Depends(get_session)):
    """模考成绩趋势 + 过线概率（按科目）。"""
    days_left = (date.fromisoformat(settings.exam_date) - datetime.now().astimezone().date()).days
    by_sub = _estimate_scores(session, user.id)
    out = {"days_left": days_left, "subjects": {}}
    for code in ("gz199", "en2"):
        series = by_sub.get(code) or []
        ests = [x["estimate"] for x in series]
        out["subjects"][code] = {
            "exams": series,
            "count": len(series),
            "forecast": _forecast(ests, days_left, GOALS[code], FULL[code]),
            "goal": GOALS[code],
            "full": FULL[code],
        }
    return out
