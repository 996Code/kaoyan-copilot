"""AI 能力：错题/题目流式讲解（SSE）+ 主观题按评分档次批改。"""

import hashlib
import json
import re
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.db import get_session
from app.core.llm import chat_complete, chat_stream, llm_ready
from app.core.settings_store import get_llm_config
from app.models import AiCache, AnswerRecord, ExamRecord, Question

router = APIRouter(prefix="/api/ai", tags=["ai"])

EXPLAIN_SYSTEM = (
    "你是一位经验丰富的考研辅导老师，正在给做错题的学生做一对一讲解。"
    "请用中文，按以下结构输出：\n"
    "1. 先一句话点出学生错在哪（结合他的错误选项）；\n"
    "2. 讲清正确解法/推理步骤（数学给关键步骤，逻辑给推理链，英语讲考点和语义）；\n"
    "3. 最后给一条举一反三的提示。\n"
    "简洁分点，可用 markdown，数学公式用 $...$ 包裹。不要复述整道题。"
)

GRADE_SYSTEM = (
    "你是一位严格按照考研阅卷标准打分的阅卷组长。根据给定的评分档次和维度，"
    "对学生的作答给出客观评分。输出必须是纯 JSON（不要 markdown 代码块），结构为：\n"
    '{"score": 数字, "max_score": 数字, "dimensions": [{"name": 维度名, "score": 数字, '
    '"max": 数字, "comment": "一句话评语"}], "strengths": ["..."], "weaknesses": ["..."], '
    '"suggestions": ["改进建议", "..."]}\n'
    "评分要贴合真实阅卷的严格度，分数从紧不给安慰分。"
)

# 主观题评分档次（按模块与题号）
RUBRICS = {
    ("translation", None): "考研英语二翻译（15分）：通读全文约150词的段落并翻译成汉语。档次：13-15分（忠实通顺，仅个别错漏）；10-12分（基本忠实，少量误解或不通顺）；7-9分（大意基本传达，有较多错译）；4-6分（仅译出部分内容）；1-3分（零散词语拼凑）。采分点为关键句的准确翻译。",
    ("writing", "en2_small"): "考研英语二小作文（10分）：应用文（邮件/通知/建议信等）。维度：格式与语域(2分)、要点覆盖(4分)、语言准确与多样(3分)、衔接连贯(1分)。",
    ("writing", "en2_big"): "考研英语二大作文（15分）：图表作文。维度：图表描述准确(5分)、观点评论合理(4分)、语言准确与多样(4分)、结构与衔接(2分)。",
    ("writing", "gz_small"): "199管综论证有效性分析（30分）：分析给定论证的缺陷。维度：缺陷识别（找出4个左右逻辑漏洞，12分）、分析说理（为何构成缺陷，12分）、结构与语言（6分）。学生未指出的缺陷不计分。",
    ("writing", "gz_big"): "199管综论说文（35分）：根据材料写论说文。维度：立意准确（10分）、论据与论证（15分）、结构与语言（10分）。跑题或立意偏差严重应大幅扣分。",
}


def _rubric_for(q: Question) -> tuple[str, str] | None:
    if q.module.code == "translation":
        return RUBRICS[("translation", None)]
    if q.module.code == "writing":
        # 管综 56=论证有效性分析 57=论说文；英二 47=小作文 48=大作文
        if q.module.subject.code == "gz199":
            return RUBRICS[("writing", "gz_small" if q.number == 56 else "gz_big")]
        return RUBRICS[("writing", "en2_small" if q.number == 47 else "en2_big")]
    return None


def _ctx_hash(question_id: int, kind: str, extra: str = "") -> str:
    return hashlib.md5(f"{question_id}|{kind}|{extra}".encode()).hexdigest()


def _question_context(session: Session, q: Question, student_answer) -> str:
    parts = []
    if q.group is not None:
        if q.group.title:
            parts.append(f"【题组】{q.group.title}")
        if q.group.material:
            parts.append(f"【共享材料】\n{q.group.material[:1500]}")
        if q.group.options:
            opts = "\n".join(f"{k}. {v}" for k, v in q.group.options.items())
            parts.append(f"【共享选项】\n{opts}")
    if q.stem:
        parts.append(f"【题干】\n{q.stem}")
    if q.options:
        opts = "\n".join(f"{o['key']}. {o['text']}" for o in q.options)
        parts.append(f"【选项】\n{opts}")
    if student_answer is not None and student_answer != "":
        parts.append(f"【学生答案】{student_answer}")
    if q.answer is not None:
        parts.append(f"【正确答案】{q.answer if q.qtype == 'single_choice' else str(q.answer)[:800]}")
    if q.analysis:
        parts.append(f"【参考解析】\n{q.analysis[:1200]}")
    return "\n\n".join(parts)


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.get("/explain/{question_id}")
async def explain(
    question_id: int,
    student_answer: str | None = None,
    session: Session = Depends(get_session),
):
    q = session.get(Question, question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="题目不存在")

    ctx = _question_context(session, q, student_answer)
    key = _ctx_hash(q.id, "explain", str(student_answer or ""))

    async def gen() -> AsyncIterator[str]:
        # 命中缓存：一次性吐出
        cache = session.scalar(
            select(AiCache).where(
                AiCache.question_id == q.id,
                AiCache.kind == "explain",
                AiCache.context_hash == key,
            )
        )
        if cache is not None and cache.response_text:
            yield _sse({"type": "delta", "text": cache.response_text})
            yield _sse({"type": "done", "cached": True})
            return

        cfg = get_llm_config(session)
        if not llm_ready(cfg):
            yield _sse({"type": "error", "message": "LLM 未配置：请管理员在「系统管理 → LLM 配置」中填写并保存"})
            return

        messages = [
            {"role": "system", "content": EXPLAIN_SYSTEM},
            {"role": "user", "content": ctx},
        ]
        full: list[str] = []
        try:
            async for chunk in chat_stream(messages, cfg):
                full.append(chunk)
                yield _sse({"type": "delta", "text": chunk})
        except Exception as e:  # noqa: BLE001
            yield _sse({"type": "error", "message": f"LLM 调用失败：{e}"})
            return
        text = "".join(full)
        session.add(
            AiCache(
                question_id=q.id, kind="explain", context_hash=key,
                response_text=text,
            )
        )
        session.commit()
        yield _sse({"type": "done", "cached": False})

    return StreamingResponse(gen(), media_type="text/event-stream")


class GradeIn(BaseModel):
    exam_id: int
    question_id: int


def _parse_json(text: str) -> dict | None:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


@router.post("/grade")
async def grade(body: GradeIn, user=Depends(current_user), session: Session = Depends(get_session)):
    rec = session.get(ExamRecord, body.exam_id)
    if rec is None or rec.user_id != user.id or rec.status != "submitted":
        raise HTTPException(status_code=409, detail="考试不存在或未交卷")
    q = session.get(Question, body.question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="题目不存在")

    rubric = _rubric_for(q)
    if rubric is None:
        raise HTTPException(status_code=400, detail="该题不是可批改的主观题")

    answer_row = session.scalar(
        select(AnswerRecord).where(
            AnswerRecord.exam_id == body.exam_id, AnswerRecord.question_id == q.id
        )
    )
    if answer_row is None or not answer_row.answer:
        raise HTTPException(status_code=400, detail="该题未作答，无法批改")

    student_text = str(answer_row.answer)
    key = _ctx_hash(q.id, "grade", f"{body.exam_id}|{student_text}")
    cache = session.scalar(
        select(AiCache).where(
            AiCache.question_id == q.id, AiCache.kind == "grade", AiCache.context_hash == key
        )
    )
    if cache is not None and cache.response_json:
        return {"result": cache.response_json, "cached": True}

    cfg = get_llm_config(session)
    if not llm_ready(cfg):
        raise HTTPException(status_code=503, detail="LLM 未配置：请管理员在「系统管理 → LLM 配置」中填写并保存")

    user_prompt = (
        f"【评分标准】\n{rubric}\n\n"
        f"【满分】{q.score or 0} 分\n\n"
        f"【题目】\n{(q.stem or '')[:800]}\n\n"
        f"【学生作答】\n{student_text[:4000]}"
    )
    try:
        text = await chat_complete(
            [
                {"role": "system", "content": GRADE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            cfg,
            temperature=0.2,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{e}") from e

    parsed = _parse_json(text)
    if parsed is None:
        raise HTTPException(status_code=502, detail="LLM 返回无法解析为 JSON")

    # 分数写入答题记录（主观题得分覆盖）
    try:
        answer_row.score = min(float(parsed.get("score", 0)), float(q.score or 0))
    except (TypeError, ValueError):
        pass
    session.add(
        AiCache(
            question_id=q.id, kind="grade", context_hash=key,
            response_json=parsed, response_text=text,
        )
    )
    session.commit()
    return {"result": parsed, "cached": False}
