from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Paper(Base, TimestampMixin):
    """整卷：一套真题/模拟卷（模考的载体）。"""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    year: Mapped[int] = mapped_column()
    name: Mapped[str] = mapped_column(String(128))
    total_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 1), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(default=180)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # real/mock

    subject: Mapped["Subject"] = relationship()
    sections: Mapped[list["PaperSection"]] = relationship(
        back_populates="paper", order_by="PaperSection.sort"
    )


class PaperSection(Base, TimestampMixin):
    """卷内分区：管综(数学/逻辑/写作)、英语二(完形/阅读/翻译/写作)。"""

    __tablename__ = "paper_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"))
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    name: Mapped[str] = mapped_column(String(64))
    sort: Mapped[int] = mapped_column(default=0)
    score_subtotal: Mapped[Optional[float]] = mapped_column(Numeric(5, 1), nullable=True)
    suggested_minutes: Mapped[Optional[int]] = mapped_column(nullable=True)
    # 原卷分区答题说明
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    paper: Mapped["Paper"] = relationship(back_populates="sections")
    items: Mapped[list["PaperQuestion"]] = relationship(
        back_populates="section", order_by="PaperQuestion.sort"
    )


class PaperQuestion(Base, TimestampMixin):
    """分区内的题目排列（含题组在卷内的顺序）。"""

    __tablename__ = "paper_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("paper_sections.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("question_groups.id"), nullable=True
    )  # 题组整体入卷时记录，前端按组渲染
    sort: Mapped[int] = mapped_column(default=0)

    section: Mapped["PaperSection"] = relationship(back_populates="items")
    question: Mapped["Question"] = relationship()

    __table_args__ = (UniqueConstraint("section_id", "question_id"),)
