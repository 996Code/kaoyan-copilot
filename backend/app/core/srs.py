"""FSRS 调度核心：卡片创建/复温/答题联动（按用户隔离）。

设计要点：任何答题行为（练习/模考/主动复习）都会推进对应卡片的记忆状态——
答错=Again（新卡则创建），答对=Good。这就是"不间断测试即复习"的实现。
"""

from datetime import datetime, timezone

from fsrs import Card, Rating, Scheduler, State
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import ReviewCard, ReviewLog

scheduler = Scheduler()

RATING_AGAIN, RATING_HARD, RATING_GOOD, RATING_EASY = 1, 2, 3, 4


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_card(session: Session, user_id: int, card_type: str, ref_id: int) -> ReviewCard | None:
    return session.scalar(
        select(ReviewCard).where(
            ReviewCard.user_id == user_id,
            ReviewCard.card_type == card_type,
            ReviewCard.ref_id == ref_id,
        )
    )


def review(
    session: Session,
    user_id: int,
    card_type: str,
    ref_id: int,
    rating: int,
    source: str,
    create_if_missing: bool = False,
) -> ReviewCard | None:
    """对卡片评分并推进 FSRS 状态。create_if_missing 时新卡先建后评。"""
    row = get_card(session, user_id, card_type, ref_id)
    if row is None:
        if not create_if_missing:
            return None
        row = ReviewCard(user_id=user_id, card_type=card_type, ref_id=ref_id, due=_now())
        session.add(row)
        session.flush()

    card = Card(
        state=State(row.state or 1),
        step=row.step or 0,
        stability=row.stability,
        difficulty=row.difficulty,
        due=row.due if row.due.tzinfo else row.due.replace(tzinfo=timezone.utc),
        last_review=(
            row.last_review.replace(tzinfo=timezone.utc)
            if row.last_review and not row.last_review.tzinfo
            else row.last_review
        ),
    )
    new_card, _log = scheduler.review_card(card, Rating(rating))

    row.due = new_card.due
    row.state = new_card.state.value
    row.step = new_card.step or 0
    row.stability = new_card.stability
    row.difficulty = new_card.difficulty
    row.last_review = new_card.last_review or _now()
    row.reps += 1
    if rating == RATING_AGAIN and row.reps > 1:
        row.lapses += 1

    session.add(ReviewLog(card_id=row.id, rating=rating, source=source))
    return row


def apply_question_answer(session: Session, user_id: int, question_id: int, correct: bool) -> None:
    """练习/模考判分后的联动：错→Again（建卡），对→Good（有卡才推进）。"""
    if correct:
        review(session, user_id, "wrong_question", question_id, RATING_GOOD, "practice", create_if_missing=False)
    else:
        review(session, user_id, "wrong_question", question_id, RATING_AGAIN, "practice", create_if_missing=True)
