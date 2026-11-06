from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Subject(Base, TimestampMixin):
    """考试科目：199 管综 / 英语二。"""

    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)  # gz199 / en2
    name: Mapped[str] = mapped_column(String(64))

    modules: Mapped[list["Module"]] = relationship(
        back_populates="subject", order_by="Module.sort"
    )


class Module(Base, TimestampMixin):
    """科目内的模块：管综(数学/逻辑/写作)、英语二(完形/阅读/翻译/写作)。"""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    code: Mapped[str] = mapped_column(String(32))  # math/logic/writing; cloze/reading/translation/writing
    name: Mapped[str] = mapped_column(String(64))
    sort: Mapped[int] = mapped_column(default=0)

    subject: Mapped["Subject"] = relationship(back_populates="modules")


class KnowledgePoint(Base, TimestampMixin):
    """知识点树（专项练习与掌握度统计的骨架），P1 阶段填充内容。"""

    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"))
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("knowledge_points.id"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort: Mapped[int] = mapped_column(default=0)

    parent: Mapped[Optional["KnowledgePoint"]] = relationship(
        remote_side="KnowledgePoint.id"
    )
