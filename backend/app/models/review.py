from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.question import Question
from app.models.word import Word


class ReviewCard(Base, TimestampMixin):
    """FSRS 记忆卡：错题卡（wrong_question）与单词卡（word）统一调度。"""

    __tablename__ = "review_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_type: Mapped[str] = mapped_column(String(16))  # wrong_question / word
    ref_id: Mapped[int] = mapped_column()  # question_id / word_id
    due: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[int] = mapped_column(default=1)  # fsrs State: 1 Learning / 2 Review / 3 Relearning
    step: Mapped[int] = mapped_column(default=0)
    stability: Mapped[Optional[float]] = mapped_column(nullable=True)
    difficulty: Mapped[Optional[float]] = mapped_column(nullable=True)
    last_review: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reps: Mapped[int] = mapped_column(default=0)
    lapses: Mapped[int] = mapped_column(default=0)

    question: Mapped[Optional[Question]] = relationship(
        primaryjoin="and_(ReviewCard.card_type=='wrong_question', foreign(ReviewCard.ref_id)==Question.id)",
        viewonly=True,
    )
    word: Mapped[Optional[Word]] = relationship(
        primaryjoin="and_(ReviewCard.card_type=='word', foreign(ReviewCard.ref_id)==Word.id)",
        viewonly=True,
    )

    __table_args__ = (UniqueConstraint("user_id", "card_type", "ref_id"),)


class ReviewLog(Base, TimestampMixin):
    """每次复习/触发的评分记录。"""

    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("review_cards.id"))
    rating: Mapped[int] = mapped_column()  # 1 Again / 2 Hard / 3 Good / 4 Easy
    source: Mapped[str] = mapped_column(String(16))  # manual / practice / exam / learn

    card: Mapped[ReviewCard] = relationship()
