"""199 管综真题入库（dollarser/kaoyan-199-guanzong-real-exams，2009-2026 共 18 套 × 57 题）。

用法：在 backend 目录下  python -I scripts/import_guanzong.py [仓库根目录]
"""

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
DATA_ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else PROJECT_ROOT / "data/raw/guanzong-exams"
EXAM_DIR = DATA_ROOT / "199管综真题_Markdown题库"
ANS_DIR = DATA_ROOT / "199管综答案_Markdown题库"
ASSET_ROOT = PROJECT_ROOT / "data/assets"
SOURCE_REPO = "dollarser/kaoyan-199-guanzong-real-exams"

# 分区定义：序号关键字 -> (模块, 分区名, 建议分值)
SECTION_KEYWORDS = [
    ("问题求解", "math", "问题求解"),
    ("条件充分性判断", "math", "条件充分性判断"),
    ("逻辑", "logic", "逻辑推理"),
    ("写作", "writing", "写作"),
]

# 条件充分性判断的固定选项（题面不重复给出）
DS_OPTIONS = [
    {"key": "A", "text": "条件（1）充分，但条件（2）不充分。"},
    {"key": "B", "text": "条件（2）充分，但条件（1）不充分。"},
    {"key": "C", "text": "条件（1）和（2）单独都不充分，但条件（1）和（2）联合起来充分。"},
    {"key": "D", "text": "条件（1）充分，条件（2）也充分。"},
    {"key": "E", "text": "条件（1）和（2）单独都不充分，条件（1）和（2）联合起来也不充分。"},
]


def qscore(number: int) -> float:
    if 1 <= number <= 25:
        return 3.0
    if 26 <= number <= 55:
        return 2.0
    return {56: 30.0, 57: 35.0}[number]


def ensure_catalog(session) -> dict:
    subject = session.scalar(select(Subject).where(Subject.code == "gz199"))
    if subject is None:
        subject = Subject(code="gz199", name="199 管理类联考综合能力")
        session.add(subject)
        session.flush()
    modules = {}
    for code, name, sort in [("math", "数学", 1), ("logic", "逻辑推理", 2), ("writing", "管综写作", 3)]:
        mod = session.scalar(
            select(Module).where(Module.subject_id == subject.id, Module.code == code)
        )
        if mod is None:
            mod = Module(subject_id=subject.id, code=code, name=name, sort=sort)
            session.add(mod)
            session.flush()
        modules[code] = mod
    return modules


def reset_gz(session, subject_id: int) -> None:
    mod_ids = [m.id for m in session.scalars(select(Module).where(Module.subject_id == subject_id))]
    q_ids = list(session.scalars(select(Question.id).where(Question.module_id.in_(mod_ids))))
    if q_ids:
        session.execute(delete(PaperQuestion).where(PaperQuestion.question_id.in_(q_ids)))
        session.execute(delete(Question).where(Question.id.in_(q_ids)))
    session.execute(delete(QuestionGroup).where(QuestionGroup.module_id.in_(mod_ids)))
    paper_ids = select(Paper.id).where(Paper.subject_id == subject_id)
    sec_ids = select(PaperSection.id).where(PaperSection.paper_id.in_(paper_ids))
    session.execute(delete(PaperQuestion).where(PaperQuestion.section_id.in_(sec_ids)))
    session.execute(delete(PaperSection).where(PaperSection.paper_id.in_(paper_ids)))
    session.execute(delete(Paper).where(Paper.subject_id == subject_id))
    print("  [reset] 已清除 gz199 旧数据")


def parse_exam_md(path: Path) -> tuple[list[dict], list[dict]]:
    """解析真题 md -> (题目列表, 共享题干组列表)

    题头变体（实测 18 套）：
      ### 第 N 题 / ### 第 N 题 · 论证有效性分析 (30 分)   标准格式
      ### N. 论证有效性分析：...                            2025 年写作
      ### N～M 题基于以下题干（[:：]）                      逻辑共享题干 -> 题组
      ### 解题说明：                                        条件判断固定选项说明，跳过
    """
    questions: list[dict] = []
    groups: list[dict] = []
    section = None
    cur: dict | None = None
    pending_group: dict | None = None

    def close() -> None:
        nonlocal cur
        if cur is not None:
            questions.append(cur)
            cur = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            close()
            pending_group = None
            for kw, mod, _ in SECTION_KEYWORDS:
                if kw in line:
                    section = f"{mod}_{'ds' if kw == '条件充分性判断' else kw}"
                    break
            continue
        if line.startswith("### "):
            mg = re.match(r"^###\s*(\d+)\s*[~～]\s*(\d+)\s*题基于以下题干", line)
            if mg:
                close()
                pending_group = {"a": int(mg.group(1)), "b": int(mg.group(2)), "lines": []}
                groups.append(pending_group)
                continue
            m = re.match(r"^###\s*(?:第\s*)?(\d+)\s*(?:题|[.．])\s*(.*)$", line)
            if m:
                close()
                n = int(m.group(1))
                in_group = (
                    pending_group is not None
                    and pending_group["a"] <= n <= pending_group["b"]
                )
                cur = {
                    "number": n,
                    "section": section,
                    "title": m.group(2).lstrip("· ").strip(),
                    "group": pending_group if in_group else None,
                    "stem_lines": [],
                    "options": [],
                    "image": None,
                    "material_lines": [],
                }
                continue
            # 解题说明等其它三级标题：内容行按当前上下文归置，标题本身丢弃
            continue
        if cur is not None:
            mo = re.match(r"^- \*\*([A-E])\*\*\s*[．.、]?\s*(.*)$", line)
            if mo:
                cur["options"].append({"key": mo.group(1), "text": mo.group(2).strip()})
                continue
            mi = re.match(r"^!\[.*\]\((images/[^)]+)\)", line)
            if mi:
                cur["image"] = mi.group(1)
                continue
            if line.startswith(">"):
                cur["material_lines"].append(re.sub(r"^>\s?", "", line))
                continue
            if line.strip() in ("---", ""):
                if cur["material_lines"]:
                    cur["material_lines"].append("")
                continue
            cur["stem_lines"].append(line)
        elif pending_group is not None:
            if line.strip() and line.strip() != "---":
                pending_group["lines"].append(re.sub(r"^>\s?", "", line).strip())
    close()

    for g in groups:
        g["material"] = "\n".join(g.pop("lines")).strip() or None
    for q in questions:
        q["stem"] = "\n".join(q.pop("stem_lines")).strip()
        mat = "\n".join(q.pop("material_lines")).strip()
        q["material"] = mat or None
        q["is_essay"] = q["section"] == "writing_writing" or (q["number"] or 0) >= 56
        # 2025 年写作：指令全在标题里（### 56. 论证有效性分析：指令），材料为正文纯文本
        if q["is_essay"]:
            m = re.match(r"^(论证有效性分析|论说文)\s*[：:]\s*(.*)$", q["title"] or "")
            if m:
                q["title"] = m.group(1)
                instruction = m.group(2).strip()
                if instruction:
                    if q["stem"]:
                        q["material"] = (
                            f"{q['material']}\n\n{q['stem']}" if q["material"] else q["stem"]
                        )
                    q["stem"] = instruction
    return questions, groups


def parse_analysis_md(path: Path) -> tuple[dict, dict, list[str]]:
    """解析解析 md -> (逐题答案+解析 {n: {'answer','analysis'}}, 速查 {n: 字母}, 警告列表)"""
    per_q: dict[int, dict] = {}
    quick: dict[int, str] = {}
    warnings: list[str] = []
    cur_n = None
    buf: list[str] = []
    in_quick = False

    def close() -> None:
        nonlocal cur_n, buf
        if cur_n is not None:
            text = "\n".join(buf).strip()
            m = re.search(r"\*\*答案\*\*\s*[：:]\s*([A-E])", text)
            if m:
                rest = text[m.end() :].strip().lstrip("，, ").strip()
                per_q[cur_n] = {"answer": m.group(1), "analysis": rest or None}
            else:
                # 写作题无答案行，整块（范文/分析要点）作为解析保留
                per_q[cur_n] = {"answer": None, "analysis": text or None}
        cur_n, buf = None, []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            close()
            in_quick = "速查" in line
            continue
        m = re.match(r"^###\s*第\s*(\d+)\s*题", line)
        if m:
            close()
            cur_n = int(m.group(1))
            continue
        if cur_n is not None:
            buf.append(line)
        elif in_quick and line.strip().startswith("-"):
            # 形如 "- 1-5 ECDBB 6-10CCBBC 11-15ADEAE 16-20CDCAC"
            for m2 in re.finditer(r"(\d+)\s*-\s*(\d+)\s*([A-E]+)", line):
                start, end, letters = int(m2.group(1)), int(m2.group(2)), m2.group(3)
                if len(letters) != end - start + 1:
                    warnings.append(f"速查段 {start}-{end} 字母数 {len(letters)} != {end - start + 1}")
                    continue
                for i, ch in enumerate(letters):
                    quick[start + i] = ch
    close()
    return per_q, quick, warnings


def copy_slice(year_dir: Path, year: int, rel: str) -> str | None:
    src = year_dir / rel
    if not src.is_file():
        return None
    rel_out = f"gz/{year}/{src.name}"
    dst = ASSET_ROOT / rel_out
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return rel_out


def import_year(session, modules: dict, year_dir: Path, ans_dir: Path) -> tuple[int, float, list[str]]:
    year = int(year_dir.name.replace("年", ""))
    exam_md = next(year_dir.glob("*真题试卷.md"))
    analysis_md = next(ans_dir.glob("*真题解析.md"))
    warns: list[str] = []

    exam_qs, shared_groups = parse_exam_md(exam_md)
    per_q, quick, awarns = parse_analysis_md(analysis_md)
    warns.extend(f"[{year}] {w}" for w in awarns)

    # 逻辑共享题干 -> QuestionGroup
    logic_module_id = modules["logic"].id
    group_rows: dict[int, QuestionGroup] = {}
    for g in shared_groups:
        grow = QuestionGroup(
            module_id=logic_module_id,
            year=year,
            title=f"第 {g['a']}～{g['b']} 题题干",
            material=g["material"],
            material_format="md",
            extra={"gtype": "logic_shared", "range": [g["a"], g["b"]]},
        )
        session.add(grow)
        session.flush()
        group_rows[g["a"]] = grow

    subject_id = modules["math"].subject_id
    paper = Paper(
        subject_id=subject_id,
        year=year,
        name=f"{year} 年 199 管理类联考综合能力真题",
        total_score=200,
        duration_minutes=180,
        source="real",
    )
    session.add(paper)
    session.flush()

    # 四个分区（数学拆 问题求解/条件充分性判断 两个分区）
    section_defs = [
        ("math", "一、问题求解", 45, 1),
        ("math", "二、条件充分性判断", 30, 2),
        ("logic", "三、逻辑推理", 60, 3),
        ("writing", "四、写作", 65, 4),
    ]
    sections = {}
    for mod_code, name, score, sort in section_defs:
        sec = PaperSection(
            paper_id=paper.id, module_id=modules[mod_code].id,
            name=name, sort=sort, score_subtotal=score,
        )
        session.add(sec)
        session.flush()
        sections[name] = sec

    def section_of(q: dict) -> PaperSection:
        n = q["number"]
        if n <= 15:
            return sections["一、问题求解"]
        if n <= 25:
            return sections["二、条件充分性判断"]
        if n <= 55:
            return sections["三、逻辑推理"]
        return sections["四、写作"]

    total_q, total_score = 0, 0.0
    for q in exam_qs:
        n = q["number"]
        mod_code = "math" if n <= 25 else ("logic" if n <= 55 else "writing")
        section = section_of(q)
        group = None
        if q.get("group") is not None:
            group = group_rows[q["group"]["a"]]
        if q["is_essay"]:
            group = QuestionGroup(
                module_id=modules[mod_code].id,
                year=year,
                title=q["title"] or ("论证有效性分析" if n == 56 else "论说文"),
                material=q["material"],
                material_format="md",
                extra={"gtype": "gz_essay"},
            )
            session.add(group)
            session.flush()

        options = q["options"]
        if not options and not q["is_essay"] and 16 <= n <= 25:
            options = DS_OPTIONS

        ans = per_q.get(n) or {}
        answer = ans.get("answer") or quick.get(n)
        if not q["is_essay"] and answer is None:
            warns.append(f"[{year}] 第 {n} 题无答案")

        img = copy_slice(year_dir, year, q["image"]) if q["image"] else None
        if q["image"] and img is None:
            warns.append(f"[{year}] 第 {n} 题切片缺失 {q['image']}")

        qrow = Question(
            module_id=modules[mod_code].id,
            group_id=group.id if group else None,
            qtype="essay" if q["is_essay"] else "single_choice",
            number=n,
            stem=q["stem"],
            stem_format="md",
            options=options or None,
            answer=answer,
            analysis=ans.get("analysis"),
            score=qscore(n),
            year=year,
            source_note=SOURCE_REPO,
            image_path=img,
            raw={"exam_file": exam_md.name},
        )
        session.add(qrow)
        session.flush()
        session.add(
            PaperQuestion(
                section_id=section.id, question_id=qrow.id,
                group_id=group.id if group else None, sort=n,
            )
        )
        total_q += 1
        total_score += qscore(n)

    return total_q, total_score, warns


def main() -> None:
    year_dirs = sorted(
        (p for p in EXAM_DIR.iterdir() if p.is_dir() and p.name.endswith("年")),
        key=lambda p: int(p.name.replace("年", "")),
    )
    print(f"发现管综真题 {len(year_dirs)} 套: {[p.name for p in year_dirs]}")

    all_warns: list[str] = []
    with SessionLocal() as session:
        modules = ensure_catalog(session)
        reset_gz(session, modules["math"].subject_id)
        for year_dir in year_dirs:
            year = year_dir.name.replace("年", "")
            ans_dir = ANS_DIR / year_dir.name
            n, score, warns = import_year(session, modules, year_dir, ans_dir)
            all_warns.extend(warns)
            ok = "OK " if (n == 57 and abs(score - 200) < 0.01) else "WARN"
            print(f"  [{ok}] {year_dir.name}: {n} 题, 总分 {score:g}")
        session.commit()

    if all_warns:
        print(f"\n{len(all_warns)} 条警告:")
        for w in all_warns:
            print("  -", w)
    print("管综入库完成")


if __name__ == "__main__":
    main()
