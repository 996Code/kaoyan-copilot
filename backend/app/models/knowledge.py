from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class KnowledgeCard(Base, TimestampMixin):
    """知识速成卡：公式/技法/谬误/句型，接入 FSRS（card_type='knowledge'）。"""

    __tablename__ = "knowledge_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(16), index=True)  # gz199 / en2
    module_name: Mapped[str] = mapped_column(String(32))               # 数学/逻辑/写作/英语写作
    category: Mapped[str] = mapped_column(String(64), index=True)      # 分类（如 等差数列）
    title: Mapped[str] = mapped_column(String(128))                    # 卡面：名称/提问
    back: Mapped[str] = mapped_column(Text)                            # 卡背：公式/要点（md+latex）
    sort: Mapped[int] = mapped_column(default=0)
