from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_session

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/subjects")
def subjects(session: Session = Depends(get_session)):
    from app.models import Module, Subject

    subs = session.scalars(select(Subject).order_by(Subject.id)).all()
    out = []
    for sub in subs:
        mods = session.scalars(
            select(Module).where(Module.subject_id == sub.id).order_by(Module.sort)
        ).all()
        out.append(
            {
                "code": sub.code,
                "name": sub.name,
                "modules": [
                    {"id": m.id, "code": m.code, "name": m.name} for m in mods
                ],
            }
        )
    return out
