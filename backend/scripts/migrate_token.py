"""HMAC 令牌迁移：users 表补 token_version 列（重置密码时 +1 使已签发令牌失效）。

幂等，可重复执行。用法：python -I scripts/migrate_token.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.core.db import engine  # noqa: E402


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0"
        ))
    print("[migrate] users.token_version 已就绪（默认 0）")


if __name__ == "__main__":
    main()
