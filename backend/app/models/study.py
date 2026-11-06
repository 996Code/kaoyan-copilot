from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.question import Question


class WrongItem(Base, TimestampMixin):
    """错题本条目：答错自动入本，「已消灭」可撤销。"""

    __tablename__ = "wrong_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    wrong_count: Mapped[int] = mapped_column(default=1)
    mastered: Mapped[bool] = mapped_column(default=False)
    last_wrong_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    question: Mapped[Question] = relationship()

    __table_args__ = (UniqueConstraint("user_id", "question_id"),)


class AiCache(Base, TimestampMixin):
    """LLM 结果缓存：同一题同一上下文不重复调用。"""

    __tablename__ = "ai_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    kind: Mapped[str] = mapped_column(String(16))  # explain / grade
    context_hash: Mapped[str] = mapped_column(String(64))
    model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (UniqueConstraint("question_id", "kind", "context_hash"),)
