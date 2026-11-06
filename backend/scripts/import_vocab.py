"""NETEM 词汇入库（exam-data/NETEMVocabulary，5530 词词频重排版）。

用法：在 backend 目录下  python -I scripts/import_vocab.py [json 路径]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import Word  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = PROJECT_ROOT / "data/raw/netem-vocab/netem_reranked_simple.json"
SOURCE = "NETEM"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    data = json.loads(path.read_text(encoding="utf-8"))
    items = next(iter(data.values()))  # 顶层唯一 key 即词条列表
    print(f"载入 {len(items)} 词（来源 {path.name}）")

    with SessionLocal() as session:
        session.execute(delete(Word).where(Word.source == SOURCE))
        for w in items:
            examples = []
            if w.get("例句"):
                examples.append(
                    {
                        "sentence": w.get("例句"),
                        "translation": w.get("例句翻译"),
                        "source": w.get("例句来源"),
                    }
                )
            session.add(
                Word(
                    headword=w["单词"],
                    phonetic=w.get("其他拼写"),
                    definition=w.get("释义"),
                    tags=[w["分类名称"]] if w.get("分类名称") else None,
                    freq_rank=w.get("序号"),
                    exam_count=w.get("真题次数"),
                    cefer=w.get("CEFR等级"),
                    examples=examples or None,
                    source=SOURCE,
                    raw=w,
                )
            )
        session.commit()
        total = session.scalar(select(Word.id).limit(1)) is not None
        print("词汇入库完成" if total else "警告：未写入任何词")


if __name__ == "__main__":
    main()
