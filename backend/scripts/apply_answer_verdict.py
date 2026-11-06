"""按 docs/data-quality/answer-verdict.md 的第三方裁决修正管综答案。

- APPLY: 改写 answer（14 处采信 DominicWay + 12 处采信第三方值）
- MARK_DISPUTED: 保留 dollarser 值但标记答案存在版本争议（6 处存疑 + 31 处未裁决）

用法：在 backend 目录下  python -I scripts/apply_answer_verdict.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import Module, Question, Subject  # noqa: E402

# (year, number) -> (final_answer, verdict, source)
APPLY = {
    # DominicWay 正确
    (2013, 2): ("E", "dominicway", "希赛网数学页"),
    (2013, 4): ("C", "dominicway", "希赛网数学页"),
    (2013, 5): ("D", "dominicway", "希赛网数学页"),
    (2013, 46): ("E", "dominicway", "研招网转载海天"),
    (2013, 49): ("A", "dominicway", "研招网转载海天"),
    (2015, 23): ("C", "dominicway", "搜狐·跨考教育"),
    (2018, 13): ("D", "dominicway", "人民网教育"),
    (2018, 15): ("A", "dominicway", "人民网教育"),
    (2018, 53): ("C", "dominicway", "人民网教育"),
    (2020, 52): ("E", "dominicway", "希赛网逻辑页"),
    (2020, 53): ("B", "dominicway", "希赛网逻辑页"),
    (2021, 27): ("B", "dominicway", "希赛网逻辑页"),
    (2021, 28): ("C", "dominicway", "希赛网逻辑页"),
    (2024, 31): ("C", "dominicway", "希赛网精讲页（陈慕泽称争议题）"),
    # 两者皆错，取第三方值（非星标）
    (2013, 31): ("B", "thirdparty", "研招网转载海天（单源）"),
    (2013, 33): ("A", "thirdparty", "研招网转载海天"),
    (2013, 39): ("E", "thirdparty", "研招网转载海天"),
    (2013, 41): ("C", "thirdparty", "研招网转载海天"),
    (2013, 43): ("B", "thirdparty", "研招网转载海天"),
    (2013, 45): ("C", "thirdparty", "研招网转载海天"),
    (2013, 48): ("C", "thirdparty", "研招网转载海天"),
    (2015, 18): ("D", "thirdparty", "跨考（单源存疑）"),
    (2015, 19): ("A", "thirdparty", "跨考（单源存疑）"),
    (2015, 20): ("B", "thirdparty", "跨考（单源存疑）"),
    (2015, 21): ("D", "thirdparty", "跨考（单源存疑）"),
    (2019, 44): ("E", "thirdparty", "希赛网（单源）"),
}

# 保留现值但标记争议：(year, number) -> reason
MARK_DISPUTED = {
    **{(2018, n): "人民网表疑错行，存疑待复核" for n in (8, 10, 11, 12, 16, 17)},
    **{(2013, n): "无第三方文本源（一题多卷年份）" for n in (6, 9, 10, 11, 12, 14, 17, 18, 20, 21, 24)},
    **{(2019, n): "希赛页缺该题" for n in (45, 51)},
    **{(2020, n): "无数学第三方源" for n in (6, 7)},
    **{(2021, n): "希赛数学页空壳" for n in (11, 14, 17, 18, 19, 20, 21)},
    **{(2022, n): "无第三方文本源" for n in (7, 8, 11, 12, 48)},
    **{(2025, n): "无第三方文本源" for n in (26, 39, 50)},
    (2026, 22): "无第三方文本源",
}


def main() -> None:
    with SessionLocal() as s:
        gz = s.scalar(select(Subject).where(Subject.code == "gz199"))
        mod_ids = [m.id for m in s.scalars(select(Module).where(Module.subject_id == gz.id))]
        qs = s.scalars(
            select(Question).where(Question.module_id.in_(mod_ids), Question.qtype == "single_choice")
        ).all()
        by_key = {(q.year, q.number): q for q in qs}

        changed = 0
        for (year, number), (final, verdict, source) in APPLY.items():
            q = by_key.get((year, number))
            if q is None:
                print(f"  [MISS] {year} 第 {number} 题不在库中")
                continue
            old = q.answer
            raw = dict(q.raw or {})
            raw["answer_verdict"] = {
                "old": old, "final": final, "winner": verdict, "source": source,
            }
            q.raw = raw
            q.answer = final
            changed += 1
            print(f"  [APPLY] {year} 第 {number} 题: {old} -> {final} ({verdict})")

        marked = 0
        for (year, number), reason in MARK_DISPUTED.items():
            q = by_key.get((year, number))
            if q is None:
                continue
            raw = dict(q.raw or {})
            raw["answer_disputed"] = {"keep": q.answer, "reason": reason}
            q.raw = raw
            marked += 1

        s.commit()
        print(f"\n修正 {changed} 题答案，标记 {marked} 题答案争议（详情见 raw 字段与 docs/data-quality/）")


if __name__ == "__main__":
    main()
