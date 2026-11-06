"""题目/题组/试卷的 JSON 序列化（答题视图默认不带答案）。"""

from app.models import Paper, PaperSection, Question, QuestionGroup


def _f(v):
    return float(v) if v is not None else None


def question_dict(q: Question, include_answer: bool = False) -> dict:
    raw = q.raw or {}
    d = {
        "id": q.id,
        "number": q.number,
        "qtype": q.qtype,
        "stem": q.stem,
        "stem_format": q.stem_format,
        "options": q.options,
        "score": _f(q.score),
        "group_id": q.group_id,
        "image_path": q.image_path,
        "has_answer": q.answer is not None,
        "disputed": bool(raw.get("answer_disputed")),
    }
    if include_answer:
        d["answer"] = q.answer
        d["analysis"] = q.analysis
    return d


def group_dict(g: QuestionGroup, questions: list[Question], include_answer: bool = False) -> dict:
    return {
        "id": g.id,
        "title": g.title,
        "material": g.material,
        "material_format": g.material_format,
        "material_image": g.material_image,
        "options": g.options,
        "gtype": (g.extra or {}).get("gtype"),
        "questions": [question_dict(q, include_answer) for q in questions],
    }


def paper_dict(
    paper: Paper,
    sections: list[PaperSection],
    items: list,  # [(section_id, sort, group_id, question)]
    include_answers: bool = False,
) -> dict:
    # 按 section 聚合：题组在首个成员处展开为整组块
    by_section: dict[int, list] = {s.id: [] for s in sections}
    emitted_groups: set[int] = set()
    for section_id, _sort, group_id, q in sorted(items, key=lambda x: (x[1] or 0)):
        blocks = by_section.setdefault(section_id, [])
        gid = group_id or q.group_id
        if gid and gid not in emitted_groups:
            group = q.group
            group_qs = [iq for _, _, g2, iq in items if (g2 or iq.group_id) == gid]
            group_qs.sort(key=lambda x: x.number or 0)
            blocks.append({"kind": "group", "group": group_dict(group, group_qs, include_answers)})
            emitted_groups.add(gid)
        elif gid is None:
            blocks.append({"kind": "question", "question": question_dict(q, include_answers)})

    return {
        "id": paper.id,
        "subject_code": paper.subject.code if paper.subject else None,
        "year": paper.year,
        "name": paper.name,
        "total_score": _f(paper.total_score),
        "duration_minutes": paper.duration_minutes,
        "sections": [
            {
                "id": s.id,
                "name": s.name,
                "sort": s.sort,
                "score_subtotal": _f(s.score_subtotal),
                "instructions": s.instructions,
                "blocks": by_section.get(s.id, []),
            }
            for s in sorted(sections, key=lambda s: s.sort)
        ],
    }


def load_paper_payload(session, paper_id: int, include_answers: bool = False) -> dict | None:
    from sqlalchemy import select

    from app.models import PaperQuestion

    paper = session.get(Paper, paper_id)
    if paper is None:
        return None
    rows = session.execute(
        select(PaperSection, PaperQuestion, Question)
        .join(PaperQuestion, PaperQuestion.section_id == PaperSection.id)
        .join(Question, PaperQuestion.question_id == Question.id)
        .where(PaperSection.paper_id == paper_id)
        .order_by(PaperSection.sort, PaperQuestion.sort)
    ).all()
    items = [(sec.id, pq.sort, pq.group_id, q) for sec, pq, q in rows]
    sections = session.scalars(
        select(PaperSection).where(PaperSection.paper_id == paper_id)
    ).all()
    return paper_dict(paper, list(sections), items, include_answers)
