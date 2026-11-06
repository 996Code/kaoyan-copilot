"""用户模块迁移：建 users 表、为既有数据表加 user_id 并归属 owner。

幂等，可重复执行。用法：python -I scripts/migrate_users.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.auth import register_user  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402

# 需要按用户隔离的数据表（ai_cache 全局共享，不在此列）
TABLES = ["exam_records", "answer_records", "wrong_items", "review_cards", "review_logs"]


def main() -> None:
    from sqlalchemy import inspect

    insp = inspect(engine)
    if not insp.has_table("users"):
        from app.models import Base  # noqa: F401
        from app.models.user import User  # noqa: F401

        Base.metadata.create_all(engine, tables=[Base.metadata.tables["users"]])
        print("[migrate] 已创建 users 表")

    with SessionLocal() as s:
        from app.models.user import User

        owner = s.scalar(
            __import__("sqlalchemy").select(User).where(User.username == settings.auth_username)
        )
        if owner is None:
            owner = register_user(s, settings.auth_username, settings.auth_password)
            s.commit()
            print(f"[migrate] 已创建 owner 用户 {settings.auth_username!r}")

        with engine.begin() as conn:
            for t in TABLES:
                conn.execute(text(f"ALTER TABLE {t} ADD COLUMN IF NOT EXISTS user_id INTEGER"))
                conn.execute(text(f"UPDATE {t} SET user_id = :uid WHERE user_id IS NULL"),
                             {"uid": owner.id})
                conn.execute(text(f"ALTER TABLE {t} ALTER COLUMN user_id SET NOT NULL"))
                # 外键
                conn.execute(text(
                    f"DO $$ BEGIN ALTER TABLE {t} ADD CONSTRAINT {t}_user_id_fkey "
                    f"FOREIGN KEY (user_id) REFERENCES users(id); EXCEPTION WHEN duplicate_object THEN NULL; END $$"
                ))
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{t}_user_id ON {t} (user_id)"))
        print(f"[migrate] {len(TABLES)} 张表已挂 user_id 并归属 {settings.auth_username!r}")

        # 唯一约束升级：wrong_items / review_cards 从全局唯一改为按用户唯一
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE wrong_items DROP CONSTRAINT IF EXISTS wrong_items_question_id_key"
            ))
            conn.execute(text(
                "ALTER TABLE wrong_items DROP CONSTRAINT IF EXISTS wrong_items_user_id_question_id_key"
            ))
            conn.execute(text("ALTER TABLE wrong_items ADD CONSTRAINT wrong_items_user_id_question_id_key UNIQUE (user_id, question_id)"))
            conn.execute(text(
                "ALTER TABLE review_cards DROP CONSTRAINT IF EXISTS review_cards_card_type_ref_id_key"
            ))
            conn.execute(text(
                "ALTER TABLE review_cards DROP CONSTRAINT IF EXISTS review_cards_user_id_card_type_ref_id_key"
            ))
            conn.execute(text("ALTER TABLE review_cards ADD CONSTRAINT review_cards_user_id_card_type_ref_id_key UNIQUE (user_id, card_type, ref_id)"))
        print("[migrate] 唯一约束已升级为按用户唯一")


if __name__ == "__main__":
    main()
