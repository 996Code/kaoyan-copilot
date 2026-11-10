"""清理英二重复导入的题目（2026-2 增量导入 bug 曾致整套题目翻倍）。

背景：import_english2.py 增量重导时先删了 paper_questions 再用子查询删题目，
子查询匹配空集 → 旧题目残留，二次导入后同 (module, year, number) 各存两份。
本脚本保留 paper_questions 引用的那份（考试在用的），删除孤儿副本；
若孤儿副本被作答/错题/复习卡引用，先并入保留份再删。幂等，可重复执行。
用法：python -I scripts/fix_en2_2026_dup.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    AiCache, AnswerRecord, Module, PaperQuestion, Question, QuestionGroup,
    ReviewCard, Subject, WrongItem,
)


def main() -> None:
    with SessionLocal() as s:
        en2 = s.scalar(select(Subject).where(Subject.code == "en2"))
        mods = {m.code: m.id for m in s.scalars(select(Module).where(Module.subject_id == en2.id))}

        # 1) 找出英二所有 (module, year, number) 重复组
        rows = s.execute(
            select(Question.module_id, Question.year, Question.number)
            .where(Question.module_id.in_(mods.values()))
            .group_by(Question.module_id, Question.year, Question.number)
            .having(func.count(Question.id) > 1)
        ).all()
        print(f"[fix] 发现 {len(rows)} 组重复 (模块,年份,题号)")

        linked = set(s.scalars(select(PaperQuestion.question_id)))
        n_del = n_merged = 0
        for module_id, year, number in rows:
            qs = list(s.scalars(
                select(Question).where(
                    Question.module_id == module_id, Question.year == year, Question.number == number
                ).order_by(Question.id)
            ))
            # 保留：paper_questions 引用的（考试在用）；无引用则留 id 最小
            keep = next((q.id for q in qs if q.id in linked), qs[0].id)
            doomed = [q for q in qs if q.id != keep]
            for q in doomed:
                # 作答并入保留份（同 user/exam 已有则丢弃孤儿行）
                for ar in s.scalars(select(AnswerRecord).where(AnswerRecord.question_id == q.id)):
                    dup = s.scalar(select(AnswerRecord).where(
                        AnswerRecord.user_id == ar.user_id,
                        AnswerRecord.exam_id == ar.exam_id,
                        AnswerRecord.question_id == keep,
                        AnswerRecord.source == ar.source,
                    ))
                    if dup is None:
                        ar.question_id = keep
                    else:
                        s.delete(ar)
                        n_merged += 1
                # 错题并入：同 user 已有保留份则累加计数后删孤儿，否则改指
                for wi in s.scalars(select(WrongItem).where(WrongItem.question_id == q.id)):
                    keep_wi = s.scalar(select(WrongItem).where(
                        WrongItem.user_id == wi.user_id, WrongItem.question_id == keep
                    ))
                    if keep_wi is None:
                        wi.question_id = keep
                    else:
                        keep_wi.wrong_count += wi.wrong_count
                        s.delete(wi)
                        n_merged += 1
                # 复习卡并入：同 user 已有保留份则删孤儿，否则改指（注意 card_type 是 wrong_question）
                for rc in s.scalars(select(ReviewCard).where(
                        ReviewCard.card_type == "wrong_question", ReviewCard.ref_id == q.id)):
                    keep_rc = s.scalar(select(ReviewCard).where(
                        ReviewCard.user_id == rc.user_id, ReviewCard.card_type == "wrong_question", ReviewCard.ref_id == keep
                    ))
                    if keep_rc is None:
                        rc.ref_id = keep
                    else:
                        s.delete(rc)
                        n_merged += 1
                # AI 缓存可再生，直接删
                s.execute(delete(AiCache).where(AiCache.question_id == q.id))
                s.delete(q)
                n_del += 1

        # 2) 删英二下不再被任何题目引用的空题组（重复导入的孤儿组）
        s.flush()  # SessionLocal autoflush=False，先把上面的删除刷库再查引用
        used_gids = set(s.scalars(select(Question.group_id).where(
            Question.module_id.in_(mods.values()), Question.group_id.is_not(None))))
        orphan_gids = list(s.scalars(select(QuestionGroup.id).where(
            QuestionGroup.module_id.in_(mods.values()), QuestionGroup.id.not_in(used_gids))))
        if orphan_gids:
            s.execute(delete(QuestionGroup).where(QuestionGroup.id.in_(orphan_gids)))
        s.commit()

        print(f"[fix] 删除重复题目 {n_del} 条，并入既有记录 {n_merged} 条，清理孤儿题组 {len(orphan_gids)} 个")
        for code, mid in sorted(mods.items()):
            n = s.scalar(select(func.count(Question.id)).where(Question.module_id == mid))
            print(f"  {code}: {n} 题")


if __name__ == "__main__":
    main()
