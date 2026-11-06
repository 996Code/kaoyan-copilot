"""系统管理迁移：users.is_admin 列、system_settings 表、LLM 配置从 .env 搬入数据库。

幂等，可重复执行。用法：python -I scripts/migrate_admin.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.settings_store import get_llm_config, set_many  # noqa: E402


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE"))
        conn.execute(text("UPDATE users SET is_admin = TRUE WHERE username = 'admin'"))

    from app.models import Base  # noqa: F401
    import app.models  # noqa: F401

    Base.metadata.create_all(engine)  # 建 system_settings 新表
    print("[migrate] users.is_admin 已就绪（admin 用户已提权），system_settings 表已创建")

    # LLM 配置从 .env 搬入数据库（仅当库中尚无值时）
    with SessionLocal() as s:
        current = get_llm_config(s)
        from_env = {
            "llm_base_url": settings.llm_base_url or "",
            "llm_api_key": settings.llm_api_key or "",
            "llm_model": settings.llm_model or "",
        }
        if not any(current.values()) and any(from_env.values()):
            set_many(s, from_env)
            print("[migrate] LLM 配置已从 .env 迁入数据库（.env 中的 LLM 配置可以删除了）")
        else:
            print(f"[migrate] 数据库 LLM 配置现状: base_url={'已设' if current['llm_base_url'] else '空'}, "
                  f"key={'已设' if current['llm_api_key'] else '空'}, model={current['llm_model'] or '空'}")


if __name__ == "__main__":
    main()
