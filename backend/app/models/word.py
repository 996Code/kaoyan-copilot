from typing import Any, Optional

from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Word(Base, TimestampMixin):
    """词汇表：NETEM 词频重排版 5530 词，英语二专属词频后续回填。"""

    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True)
    headword: Mapped[str] = mapped_column(String(64), index=True)
    phonetic: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    freq_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exam_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cefer: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    examples: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    # 英语二 16 套真题语料自算的词频：{count, rank, years:[...]}
    en2_freq: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    __table_args__ = (UniqueConstraint("headword", "source"),)
