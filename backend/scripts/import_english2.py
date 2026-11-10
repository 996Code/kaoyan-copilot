"""英语二真题入库（LIziak112/structured-kaoyan-structured 的 *-2 目录，2010-2025 共 16 套）。

用法：在 backend 目录下  python -I scripts/import_english2.py [数据根目录]
默认数据根目录：../data/raw/english2-structured
"""

import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Module,
    Paper,
    PaperQuestion,
    PaperSection,
    Question,
    QuestionGroup,
    Subject,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_arg1 = sys.argv[1] if len(sys.argv) > 1 else None
# argv[1] 形如 "2026-2" 时为增量导入单套；否则视为数据根目录（向后兼容）
ONLY = _arg1 if _arg1 and re.fullmatch(r"\d{4}-2", _arg1) else None
DATA_ROOT = Path(_arg1) if _arg1 and ONLY is None else PROJECT_ROOT / "data/raw/english2-structured"
ASSET_ROOT = PROJECT_ROOT / "data/assets"

SOURCE_REPO = "LIziak112/structured-kaoyan-english"

# 题组类型 -> 模块 code / 题型
GROUP_MODULE = {
    "cloze": "cloze",
    "reading": "reading",
    "matching": "reading",
    "heading_matching": "reading",
    "translation_full": "translation",
    "translation": "translation",
    "writing": "writing",
}
GROUP_QTYPE = {
    "cloze": "single_choice",
    "reading": "single_choice",
    "matching": "single_choice",
    "heading_matching": "single_choice",
    "translation_full": "translation",
    "translation": "translation",
    "writing": "essay",
}

# 题组缺 type 字段时按分区序号推断（2023-2 存在此情况）
SECTION_IDX_TYPE = {
    0: "cloze",
    1: "reading",
    2: "matching",
    3: "translation_full",
    4: "writing",
    5: "writing",
}
# 分区缺总分时的标准分值
SECTION_IDX_SCORE = {0: 10, 1: 40, 2: 10, 3: 15, 4: 10, 5: 15}

# 每套卷的期望校验值
EXPECTED_QUESTIONS = 48
EXPECTED_SCORE = 100.0


def ensure_catalog(session: object) -> dict:
    """确保 en2 科目与四个模块存在，返回 code -> Module。"""
    subject = session.scalar(select(Subject).where(Subject.code == "en2"))
    if subject is None:
        subject = Subject(code="en2", name="考研英语（二）")
        session.add(subject)
        session.flush()

    modules = {}
    for code, name, sort in [
        ("cloze", "完形填空", 1),
        ("reading", "阅读理解", 2),
        ("translation", "翻译", 3),
        ("writing", "英语写作", 4),
    ]:
        mod = session.scalar(
            select(Module).where(Module.subject_id == subject.id, Module.code == code)
        )
        if mod is None:
            mod = Module(subject_id=subject.id, code=code, name=name, sort=sort)
            session.add(mod)
            session.flush()
        modules[code] = mod
    return modules


def reset_en2(session: object, subject_id: int) -> None:
    """按科目重导：删除该科目全部题目/题组/试卷。"""
    mod_ids = [
        m.id for m in session.scalars(select(Module).where(Module.subject_id == subject_id))
    ]
    q_ids = list(
        session.scalars(select(Question.id).where(Question.module_id.in_(mod_ids)))
    )
    if q_ids:
        session.execute(delete(PaperQuestion).where(PaperQuestion.question_id.in_(q_ids)))
        session.execute(delete(Question).where(Question.id.in_(q_ids)))
    session.execute(
        delete(QuestionGroup).where(QuestionGroup.module_id.in_(mod_ids))
    )
    paper_ids = select(Paper.id).where(Paper.subject_id == subject_id)
    sec_ids = select(PaperSection.id).where(PaperSection.paper_id.in_(paper_ids))
    session.execute(delete(PaperQuestion).where(PaperQuestion.section_id.in_(sec_ids)))
    session.execute(delete(PaperSection).where(PaperSection.paper_id.in_(paper_ids)))
    session.execute(delete(Paper).where(Paper.subject_id == subject_id))
    print("  [reset] 已清除 en2 旧数据")


def copy_image(set_dir: Path, set_name: str, ref: str, number: int) -> str | None:
    """把题组引用的图片复制到 data/assets/en2/<套>/<文件>，返回相对路径。"""
    rel_dir = f"en2/{set_name}"
    candidates = [set_dir / "assets" / Path(ref).name]
    candidates.extend((set_dir / "assets").glob(f"*q{number}.*"))
    for src in candidates:
        if src.is_file():
            dst = ASSET_ROOT / rel_dir / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return f"{rel_dir}/{src.name}"
    return None


def import_paper(session: object, modules: dict, set_dir: Path) -> tuple[int, float]:
    set_name = set_dir.name  # 如 2024-2
    year = int(set_name.split("-")[0])
    data = json.loads((set_dir / f"{set_name}.json").read_text(encoding="utf-8"))

    paper = Paper(
        subject_id=modules["cloze"].subject_id,
        year=year,
        name=f"{year} 年考研英语（二）真题",
        total_score=100,
        duration_minutes=180,
        source="real",
    )
    session.add(paper)
    session.flush()

    total_q = 0
    total_score = 0.0
    for sec_idx, sec in enumerate(data["sections"], start=1):
        # 分区模块取其第一个题组的类型推断（同分区题组类型一致）
        gtype = sec["groups"][0].get("type") or SECTION_IDX_TYPE[sec_idx - 1]
        module_code = GROUP_MODULE.get(gtype)
        if module_code is None:
            raise ValueError(f"{set_name}: 未知题组类型 {gtype!r}")

        # 分区内每题默认分值：分区总分摊到每题（早年份题目级分值缺失）
        sec_score = sec.get("score") or SECTION_IDX_SCORE[sec_idx - 1]
        n_questions = sum(len(g["questions"]) for g in sec["groups"])
        per_q_score = round(sec_score / n_questions, 2) if n_questions else None

        section = PaperSection(
            paper_id=paper.id,
            module_id=modules[module_code].id,
            name=sec["title"],
            sort=sec_idx,
            score_subtotal=sec.get("score"),
            instructions=sec.get("instructions"),
        )
        session.add(section)
        session.flush()

        for g in sec["groups"]:
            group_type = g.get("type") or gtype
            passage = g.get("passage")
            material = "\n\n".join(passage) if isinstance(passage, list) else passage

            group = QuestionGroup(
                module_id=modules[module_code].id,
                year=year,
                title=g.get("title"),
                material=material,
                material_format="text",
                options=g.get("options"),
                extra={"gtype": group_type, "images": g.get("images")},
                # 图片在题目循环里回填
            )
            session.add(group)
            session.flush()

            # 题组配图（英二大作文图表）
            image_refs = g.get("images") or []
            if image_refs:
                rel = copy_image(set_dir, set_name, str(image_refs[0]), 0)
                if rel:
                    group.material_image = rel

            for gq in g["questions"]:
                number = gq.get("number")
                qtype = GROUP_QTYPE[group_type]
                q_score = (
                    gq.get("score") if gq.get("score") is not None else per_q_score
                )
                opts = None
                if gq.get("options"):
                    opts = [
                        {"key": k, "text": v} for k, v in sorted(gq["options"].items())
                    ]
                q = Question(
                    module_id=modules[module_code].id,
                    group_id=group.id,
                    qtype=qtype,
                    number=number,
                    stem=gq.get("stem") or "",
                    stem_format="md",
                    options=opts,
                    answer=gq.get("answer"),
                    analysis=gq.get("explanation"),
                    score=q_score,
                    year=year,
                    source_note=SOURCE_REPO,
                    raw={"dir": set_name, "gtype": group_type},
                )
                session.add(q)
                session.flush()
                session.add(
                    PaperQuestion(
                        section_id=section.id,
                        question_id=q.id,
                        group_id=group.id,
                        sort=number or total_q + 1,
                    )
                )
                total_q += 1
                total_score += float(q_score or 0)

    return total_q, total_score


def main() -> None:
    only = ONLY  # 增量模式：只导入指定套（如 2026-2），不重置旧数据
    set_dirs = sorted(
        p for p in DATA_ROOT.joinpath("data").iterdir()
        if p.is_dir() and re.fullmatch(r"\d{4}-2", p.name)
        and (only is None or p.name == only)
    )
    print(f"发现英语二真题 {len(set_dirs)} 套: {[p.name for p in set_dirs]}")

    with SessionLocal() as session:
        modules = ensure_catalog(session)
        subject_id = modules["cloze"].subject_id
        if only is None:
            reset_en2(session, subject_id)
        else:
            # 增量幂等：该年份已有卷则先删（题被作答引用时不删，跳过并提示）
            from app.models import AnswerRecord as _AR

            old = session.scalar(select(Paper).where(Paper.subject_id == subject_id, Paper.year == int(only.split("-")[0])))
            if old is not None:
                qids = select(Question.id).join(PaperQuestion, PaperQuestion.question_id == Question.id).join(PaperSection, PaperSection.id == PaperQuestion.section_id).where(PaperSection.paper_id == old.id)
                used = session.scalar(select(_AR.id).where(_AR.question_id.in_(qids)).limit(1))
                if used:
                    print(f"  [skip] {only} 已存在且有作答记录，跳过（如需重导请先清理该卷作答）")
                    session.rollback()
                    return
                print(f"  [reset] {only} 已存在且无作答，重建该套")
                # 先物化 id 列表再删除：子查询与 DELETE 同事务时若先删关联行，后续 in_() 会匹配空集（曾致题目翻倍）
                sec_ids = list(session.scalars(select(PaperSection.id).where(PaperSection.paper_id == old.id)))
                qids = list(session.scalars(select(PaperQuestion.question_id).where(PaperQuestion.section_id.in_(sec_ids))))
                gids = list(session.scalars(select(Question.group_id).where(Question.id.in_(qids), Question.group_id.is_not(None))))
                session.execute(delete(PaperQuestion).where(PaperQuestion.section_id.in_(sec_ids)))
                session.execute(delete(PaperSection).where(PaperSection.paper_id == old.id))
                session.execute(delete(Question).where(Question.id.in_(qids)))
                session.execute(delete(QuestionGroup).where(QuestionGroup.id.in_(gids)))
                session.execute(delete(Paper).where(Paper.id == old.id))
                session.commit()

        for set_dir in set_dirs:
            n, score = import_paper(session, modules, set_dir)
            ok = "OK " if (n == EXPECTED_QUESTIONS and abs(score - EXPECTED_SCORE) < 0.01) else "WARN"
            print(f"  [{ok}] {set_dir.name}: {n} 题, 总分 {score:g}")

        session.commit()

    print("英语二入库完成")


if __name__ == "__main__":
    main()
