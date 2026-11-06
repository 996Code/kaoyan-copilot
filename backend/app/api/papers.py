from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.models import Paper, PaperSection, Subject
from app.api.serialize import load_paper_payload

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("")
def list_papers(subject: str, session: Session = Depends(get_session)):
    rows = session.execute(
        select(Paper, func.count(func.distinct(PaperSection.id)))
        .join(Subject, Paper.subject_id == Subject.id)
        .outerjoin(PaperSection, PaperSection.paper_id == Paper.id)
        .where(Subject.code == subject)
        .group_by(Paper.id)
        .order_by(Paper.year.desc())
    ).all()
    return [
        {
            "id": p.id,
            "year": p.year,
            "name": p.name,
            "total_score": float(p.total_score) if p.total_score else None,
            "duration_minutes": p.duration_minutes,
        }
        for p, _ in rows
    ]


@router.get("/{paper_id}")
def paper_detail(paper_id: int, session: Session = Depends(get_session)):
    payload = load_paper_payload(session, paper_id, include_answers=False)
    if payload is None:
        raise HTTPException(status_code=404, detail="试卷不存在")
    return payload
