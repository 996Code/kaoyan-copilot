"""整卷模考：开考（断点续答）、保存、交卷判分、历史。"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serialize import load_paper_payload
from app.core.auth import current_user
from app.core.db import get_session
from app.models import AnswerRecord, ExamRecord, Question, Subject
from app.models.user import User

router = APIRouter(prefix="/api/exams", tags=["exams"])

GRACE_SECONDS = 15  # 网络/提交延迟宽限


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _record_dict(rec: ExamRecord) -> dict:
    return {
        "id": rec.id,
        "paper_id": rec.paper_id,
        "status": rec.status,
        "duration_minutes": rec.duration_minutes,
        "started_at": rec.started_at,
        "deadline_at": rec.deadline_at,
        "submitted_at": rec.submitted_at,
        "overtime": rec.overtime,
        "objective_score": float(rec.objective_score) if rec.objective_score is not None else None,
        "objective_total": float(rec.objective_total) if rec.objective_total is not None else None,
        "server_now": _now(),
    }


def _answers_map(session: Session, exam_id: int) -> dict:
    rows = session.scalars(
        select(AnswerRecord).where(AnswerRecord.exam_id == exam_id)
    ).all()
    return {str(r.question_id): r.answer for r in rows}


def _paper_questions(session: Session, paper_id: int) -> list[Question]:
    from app.models import PaperQuestion, PaperSection

    return list(
        session.scalars(
            select(Question)
            .join(PaperQuestion, PaperQuestion.question_id == Question.id)
            .join(PaperSection, PaperSection.id == PaperQuestion.section_id)
            .where(PaperSection.paper_id == paper_id)
        ).all()
    )


def _save_answers(session: Session, rec: ExamRecord, answers: dict) -> None:
    existing = {
        r.question_id: r
        for r in session.scalars(
            select(AnswerRecord).where(AnswerRecord.exam_id == rec.id)
        ).all()
    }
    for qid_str, value in answers.items():
        try:
            qid = int(qid_str)
        except (TypeError, ValueError):
            continue
        row = existing.get(qid)
        if row is None:
            row = AnswerRecord(
                user_id=rec.user_id, exam_id=rec.id, question_id=qid, answer=value, source="exam"
            )
            session.add(row)
            existing[qid] = row
        else:
            row.answer = value


def _payload(session: Session, rec: ExamRecord, include_answers: bool, results: dict | None = None):
    paper = load_paper_payload(session, rec.paper_id, include_answers=include_answers)
    return {"exam": _record_dict(rec), "paper": paper, "answers": _answers_map(session, rec.id), "results": results}


class StartIn(BaseModel):
    paper_id: int


class AnswersIn(BaseModel):
    answers: dict


@router.post("")
def start_exam(body: StartIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    """开考；若该卷已有进行中的考试则返回原记录（断点续答）。"""
    rec = session.scalar(
        select(ExamRecord).where(
            ExamRecord.user_id == user.id,
            ExamRecord.paper_id == body.paper_id,
            ExamRecord.status == "in_progress",
        )
    )
    if rec is None:
        from app.models import Paper

        paper = session.get(Paper, body.paper_id)
        if paper is None:
            raise HTTPException(status_code=404, detail="试卷不存在")
        rec = ExamRecord(
            user_id=user.id,
            paper_id=paper.id,
            duration_minutes=paper.duration_minutes,
            deadline_at=_now() + timedelta(minutes=paper.duration_minutes),
        )
        session.add(rec)
        session.commit()
    session.refresh(rec)
    return _payload(session, rec, include_answers=False)


@router.get("/history")
def history(
    paper_id: int | None = None,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    q = (
        select(ExamRecord)
        .where(ExamRecord.user_id == user.id, ExamRecord.status == "submitted")
        .order_by(ExamRecord.submitted_at.desc())
    )
    if paper_id:
        q = q.where(ExamRecord.paper_id == paper_id)
    return [_record_dict(r) for r in session.scalars(q.limit(50)).all()]


def _build_results(session: Session, rec: ExamRecord) -> dict:
    """从已保存的作答记录重建逐题判分结果（报告页刷新/回看用）。"""
    questions = _paper_questions(session, rec.paper_id)
    rows = {
        r.question_id: r
        for r in session.scalars(
            select(AnswerRecord).where(AnswerRecord.exam_id == rec.id)
        ).all()
    }
    results = {}
    for q in questions:
        row = rows.get(q.id)
        results[str(q.id)] = {
            "your_answer": row.answer if row else None,
            "is_correct": row.is_correct if row else None,
            "score_earned": float(row.score) if row is not None and row.score is not None else None,
            "score_total": float(q.score) if q.score is not None else None,
        }
    return results


@router.get("/{exam_id}")
def get_exam(exam_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    rec = session.get(ExamRecord, exam_id)
    if rec is None or rec.user_id != user.id:
        raise HTTPException(status_code=404, detail="考试不存在")
    include = rec.status == "submitted"
    results = _build_results(session, rec) if include else None
    return _payload(session, rec, include_answers=include, results=results)


@router.put("/{exam_id}/answers")
def save_answers(
    exam_id: int, body: AnswersIn, user: User = Depends(current_user), session: Session = Depends(get_session)
):
    rec = session.get(ExamRecord, exam_id)
    if rec is None or rec.user_id != user.id or rec.status != "in_progress":
        raise HTTPException(status_code=409, detail="考试不存在或已交卷")
    _save_answers(session, rec, body.answers)
    session.commit()
    return {"saved": len(body.answers), "server_now": _now()}


@router.post("/{exam_id}/submit")
def submit(exam_id: int, body: AnswersIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    rec = session.get(ExamRecord, exam_id)
    if rec is None or rec.user_id != user.id or rec.status != "in_progress":
        raise HTTPException(status_code=409, detail="考试不存在或已交卷")

    _save_answers(session, rec, body.answers or {})
    session.flush()  # autoflush 已关闭：判分前必须显式落库，否则查询看不到刚保存的作答

    questions = _paper_questions(session, rec.paper_id)
    answer_rows = {
        r.question_id: r
        for r in session.scalars(
            select(AnswerRecord).where(AnswerRecord.exam_id == rec.id)
        ).all()
    }

    results: dict[str, dict] = {}
    obj_score = 0.0
    obj_total = 0.0
    for q in questions:
        row = answer_rows.get(q.id)
        your = row.answer if row else None
        entry = {
            "your_answer": your,
            "is_correct": None,
            "score_earned": None,
            "score_total": float(q.score) if q.score is not None else None,
        }
        if q.qtype == "single_choice":
            obj_total += float(q.score or 0)
            correct = your is not None and str(your).strip().upper() == str(q.answer).strip().upper()
            earned = float(q.score or 0) if correct else 0.0
            # 未作答：判 0 分但不算「错」（不进错题本、不建 FSRS 卡）
            if your is not None:
                from app.core.srs import apply_question_answer

                apply_question_answer(session, user.id, q.id, bool(correct), source="exam")
                if correct is False:
                    from app.api.wrongbook import record_wrong

                    record_wrong(session, user.id, q.id)
            obj_score += earned
            entry["is_correct"] = correct
            entry["score_earned"] = earned
            if row:
                row.is_correct = correct
                row.score = earned
        results[str(q.id)] = entry

    now = _now()
    deadline = rec.deadline_at if rec.deadline_at.tzinfo else rec.deadline_at.replace(tzinfo=timezone.utc)
    rec.overtime = now > deadline + timedelta(seconds=GRACE_SECONDS)
    rec.status = "submitted"
    rec.submitted_at = now
    rec.objective_score = round(obj_score, 1)
    rec.objective_total = round(obj_total, 1)
    session.commit()
    session.refresh(rec)

    return _payload(session, rec, include_answers=True, results=results)
