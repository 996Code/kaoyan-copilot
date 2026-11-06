"""入库数据对账校验。在 backend 目录下  python -I scripts/verify_data.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Module,
    Paper,
    PaperQuestion,
    PaperSection,
    Question,
    QuestionGroup,
    Subject,
    Word,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = PROJECT_ROOT / "data/assets"

failures: list[str] = []


def check(label: str, actual, expected) -> None:
    ok = actual == expected
    mark = "OK " if ok else "FAIL"
    print(f"  [{mark}] {label}: {actual} (期望 {expected})")
    if not ok:
        failures.append(label)


def main() -> None:
    with SessionLocal() as s:
        print("== 科目与模块 ==")
        for sub in s.scalars(select(Subject)):
            mods = s.scalars(select(Module).where(Module.subject_id == sub.id))
            print(f"  {sub.code}({sub.name}): " + ", ".join(f"{m.code}({m.name})" for m in mods))

        print("== 英二对账 ==")
        for code, expect_q, expect_g in [
            ("cloze", 320, 16),        # 16 套 × 20 空
            ("reading", 400, 80),      # 16 套 × (20 PartA + 5 PartB) 题组 16×(4+1)
            ("translation", 16, 16),
            ("writing", 32, 32),
        ]:
            m = s.scalar(select(Module).where(Module.code == code))
            if m is None:
                check(f"模块 {code} 存在", False, True)
                continue
            n = s.scalar(select(func.count(Question.id)).where(Question.module_id == m.id))
            g = s.scalar(select(func.count(QuestionGroup.id)).where(QuestionGroup.module_id == m.id))
            check(f"{code} 题数", n, expect_q)
            check(f"{code} 题组数", g, expect_g)

        en2_sub = s.scalar(select(Subject).where(Subject.code == "en2"))
        check("英二试卷数", s.scalar(select(func.count(Paper.id)).where(Paper.subject_id == en2_sub.id)), 16)
        check("英二分区数", s.scalar(select(func.count(PaperSection.id)).join(Paper).where(Paper.subject_id == en2_sub.id)), 16 * 6)
        check("英二卷题关联", s.scalar(select(func.count(PaperQuestion.id)).join(PaperSection).join(Paper).where(Paper.subject_id == en2_sub.id)), 768)

        print("== 答案与解析完整性 ==")
        check("answer 为空", s.scalar(select(func.count(Question.id)).where(Question.answer.is_(None))), 0)
        check("single_choice 无选项",
              s.scalar(select(func.count(Question.id)).where(Question.qtype == "single_choice", Question.options.is_(None))),
              0)
        # 管综 36 道写作题允许无 analysis 之外的空解析为 0
        check("analysis 为空", s.scalar(select(func.count(Question.id)).where(Question.analysis.is_(None))), 0)

        print("== 主观题参考答案（翻译/作文；管综写作无标准范文，仅查英二） ==")
        for qt in ("translation", "essay"):
            n = s.scalar(
                select(func.count(Question.id))
                .join(Module, Question.module_id == Module.id)
                .where(Module.subject_id == en2_sub.id, Question.qtype == qt, Question.answer.is_(None))
            )
            check(f"en2 {qt} 缺参考答案", n, 0)

        print("== 配图文件 ==")
        imgs = s.scalars(select(QuestionGroup.material_image).where(QuestionGroup.material_image.is_not(None))).all()
        # 已知缺口：2012/2025 大作文图表在源仓库（LIziak112）中缺失，其余 14 年齐全
        check("大作文图表题组数", len(imgs), 14)
        for p in imgs:
            if not (ASSET_ROOT / p).is_file():
                failures.append(f"图片缺失 {p}")
                print(f"  [FAIL] 图片缺失: {p}")
        if all((ASSET_ROOT / p).is_file() for p in imgs):
            print(f"  [OK ] {len(imgs)} 张图表全部存在于 data/assets")

        print("== 管综对账 ==")
        for code, expect_q, expect_g in [
            ("math", 18 * 25, 0),      # 18 套 × 25 题（问题求解+条件判断）
            ("logic", 18 * 30, 52),     # 52 个共享题干题组（18 套合计）
            ("writing", 18 * 2, 36),    # 每题一个材料题组
        ]:
            m = s.scalar(select(Module).where(Module.code == code, Module.subject_id == Subject.id).join(Subject).where(Subject.code == "gz199"))
            if m is None:
                check(f"管综模块 {code} 存在", False, True)
                continue
            n = s.scalar(select(func.count(Question.id)).where(Question.module_id == m.id))
            g = s.scalar(select(func.count(QuestionGroup.id)).where(QuestionGroup.module_id == m.id))
            check(f"gz {code} 题数", n, expect_q)
            if expect_g:
                check(f"gz {code} 题组数", g, expect_g)

        gz_sub = s.scalar(select(Subject).where(Subject.code == "gz199"))
        check("管综试卷数", s.scalar(select(func.count(Paper.id)).where(Paper.subject_id == gz_sub.id)), 18)
        check("管综分区数", s.scalar(select(func.count(PaperSection.id)).join(Paper).where(Paper.subject_id == gz_sub.id)), 18 * 4)
        gz_choice_no_ans = s.scalar(
            select(func.count(Question.id))
            .join(Module, Question.module_id == Module.id)
            .where(Module.subject_id == gz_sub.id, Question.qtype == "single_choice", Question.answer.is_(None))
        )
        check("管综选择题缺答案", gz_choice_no_ans, 0)
        gz_img = s.scalar(
            select(func.count(Question.id))
            .join(Module, Question.module_id == Module.id)
            .where(Module.subject_id == gz_sub.id, Question.qtype == "single_choice", Question.image_path.is_not(None))
        )
        print(f"  [INFO] 管综带原卷切片题数: {gz_img}（校对用）")

        print("== 词汇 ==")
        check("词汇总量", s.scalar(select(func.count(Word.id))), 5530)
        top = s.scalars(select(Word).order_by(Word.freq_rank).limit(3)).all()
        print("  词频前3:", [f"{w.headword}({w.freq_rank})" for w in top])

        print("== 内容抽查：2024 年完形第 1 题 ==")
        q = s.scalar(
            select(Question)
            .where(Question.year == 2024, Question.qtype == "single_choice", Question.number == 1)
            .join(QuestionGroup, Question.group_id == QuestionGroup.id)
            .where(QuestionGroup.extra["gtype"].astext == "cloze")
        )
        if q is None:
            failures.append("2024 完形第 1 题未找到")
            print("  [FAIL] 未找到")
        else:
            print(f"  第1题选项: {[o['key'] for o in q.options]} 答案: {q.answer}")
            check("2024 完形第 1 题答案", q.answer, "C")

    print()
    if failures:
        print(f"校验未通过 {len(failures)} 项: {failures}")
        sys.exit(1)
    print("全部校验通过 ✓")


if __name__ == "__main__":
    main()
