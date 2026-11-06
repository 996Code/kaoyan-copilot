from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.paper import Paper
from app.models.question import Question


class ExamRecord(Base, TimestampMixin):
    """一次整卷模考（含断点续答状态）。"""

    __tablename__ = "exam_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"))
    status: Mapped[str] = mapped_column(String(16), default="in_progress")  # in_progress/submitted
    duration_minutes: Mapped[int] = mapped_column(default=180)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    overtime: Mapped[bool] = mapped_column(default=False)
    objective_score: Mapped[Optional[float]] = mapped_column(Numeric(6, 1), nullable=True)
    objective_total: Mapped[Optional[float]] = mapped_column(Numeric(6, 1), nullable=True)

    paper: Mapped[Paper] = relationship()
    answers: Mapped[list["AnswerRecord"]] = relationship(back_populates="exam")


class AnswerRecord(Base, TimestampMixin):
    """作答记录：模考（挂 exam）或专项练习（exam 为空，允许多次）。"""

    __tablename__ = "answer_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exam_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exam_records.id"), nullable=True
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    answer: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Numeric(5, 1), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="exam")  # exam/practice

    exam: Mapped[Optional[ExamRecord]] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship()

    # 模考内每题唯一（练习的 exam_id 为 NULL，PostgreSQL 视 NULL 互异，可多次作答）
    __table_args__ = (UniqueConstraint("exam_id", "question_id"),)
