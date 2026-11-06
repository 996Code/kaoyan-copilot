from typing import Any, Optional

from sqlalchemy import Column, ForeignKey, Numeric, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.catalog import Module

# 题目 <-> 知识点 多对多
question_knowledge_point = Table(
    "question_knowledge_point",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id"), primary_key=True),
    Column("knowledge_point_id", ForeignKey("knowledge_points.id"), primary_key=True),
)


class QuestionGroup(Base, TimestampMixin):
    """共享材料题组：阅读一篇文章带 N 题、完形语段带 20 空、翻译段落、写作材料。

    英语二整卷的骨架。独立题（管综数学/逻辑）group_id 为空。
    """

    __tablename__ = "question_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    year: Mapped[Optional[int]] = mapped_column(nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # 共享材料正文；完形空格统一用 {{1}}..{{20}} 标记
    material: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    material_format: Mapped[str] = mapped_column(String(16), default="text")  # text/md/latex
    # 英二大作文图表等配图（相对 data/assets 的路径）
    material_image: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # 题组级共享选项（英二新题型 Part B 的 A-G 语句）
    options: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="group", order_by="Question.number"
    )


class Question(Base, TimestampMixin):
    """最小题目单元：单选题 / 翻译 / 作文等。"""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("question_groups.id"), nullable=True
    )
    qtype: Mapped[str] = mapped_column(String(32))  # single_choice/translation/essay
    number: Mapped[Optional[int]] = mapped_column(nullable=True)  # 卷内题号
    stem: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stem_format: Mapped[str] = mapped_column(String(16), default="md")
    # 选项 [{"key":"A","text":"..."}]
    options: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # "A" / ["A","C"] / 参考译文 / 范文文本
    answer: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Numeric(5, 1), nullable=True)
    difficulty: Mapped[Optional[int]] = mapped_column(nullable=True)  # 1-5，后续评估
    year: Mapped[Optional[int]] = mapped_column(nullable=True)
    source_note: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # 原卷 PNG 切片（相对 data/assets 的路径，校对用）
    image_path: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    group: Mapped[Optional[QuestionGroup]] = relationship(back_populates="questions")
    module: Mapped[Module] = relationship()
    knowledge_points: Mapped[list["KnowledgePoint"]] = relationship(
        secondary=question_knowledge_point, lazy="selectin"
    )
