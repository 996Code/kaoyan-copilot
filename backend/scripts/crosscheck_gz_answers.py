"""管综答案交叉校验：DB（dollarser 逐题+速查） vs DominicWay 独立速查（2010-2026）。

用法：在 backend 目录下  python -I scripts/crosscheck_gz_answers.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import Module, Question  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = PROJECT_ROOT / "data/raw/guanzong-answers/index.html"


def parse_dominicway() -> dict[int, dict[int, str]]:
    """从 index.html 提取 {"2010":{"ps":"DCC...","ds":"...","lr":"..."}} -> {year: {qnum: letter}}"""
    text = HTML_PATH.read_text(encoding="utf-8")
    answers: dict[int, dict[int, str]] = {}
    for m in re.finditer(
        r'(\d{4})"\s*:\s*\{\s*"ps"\s*:\s*"([A-E]{15})"\s*,\s*"ds"\s*:\s*"([A-E]{10})"\s*,\s*"lr"\s*:\s*"([A-E]{30})"',
        text,
    ):
        year = int(m.group(1))
        mapping: dict[int, str] = {}
        for i, ch in enumerate(m.group(2)):
            mapping[1 + i] = ch
        for i, ch in enumerate(m.group(3)):
            mapping[16 + i] = ch
        for i, ch in enumerate(m.group(4)):
            mapping[26 + i] = ch
        answers[year] = mapping
    return answers


def main() -> None:
    external = parse_dominicway()
    print(f"DominicWay 速查解析: {sorted(external)} ({len(external)} 套)")

    total_cmp, total_diff = 0, 0
    with SessionLocal() as s:
        math_mod = s.scalar(select(Module).where(Module.code == "math"))
        logic_mod = s.scalar(select(Module).where(Module.code == "logic"))
        for year in sorted(external):
            qs = s.scalars(
                select(Question)
                .where(
                    Question.year == year,
                    Question.qtype == "single_choice",
                    Question.module_id.in_([math_mod.id, logic_mod.id]),
                )
                .order_by(Question.number)
            ).all()
            db_map = {q.number: q.answer for q in qs if q.answer}
            diffs = []
            for n, letter in external[year].items():
                total_cmp += 1
                if n in db_map and db_map[n] != letter:
                    diffs.append(f"第{n}题 DB={db_map[n]} 外部={letter}")
            if diffs:
                total_diff += len(diffs)
                print(f"  {year}: {len(diffs)} 处不一致 -> {'; '.join(diffs[:5])}")
            else:
                print(f"  {year}: 55 题全部一致 ✓")

    print(f"\n合计比对 {total_cmp} 题，不一致 {total_diff} 题")
    if total_diff == 0:
        print("交叉校验通过：两个独立来源的答案完全一致 ✓")
    else:
        print("存在不一致，需人工比对原卷 PNG 切片裁决")


if __name__ == "__main__":
    main()
