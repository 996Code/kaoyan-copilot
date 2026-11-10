"""时区迁移：kaoyan 库会话时区设为 Asia/Shanghai，让 API 返回北京时间。

timestamptz 存的是绝对时刻，此设置只影响返回格式（+08:00）与 func.now() 的呈现，
不动任何数据；对同实例其他数据库无影响。幂等，可重复执行。
用法：python -I scripts/migrate_timezone.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))



from app.core.db import engine  # noqa: E402


def main() -> None:
    # ALTER DATABASE 不能在事务块内执行，须用 AUTOCOMMIT 连接
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        dbname = conn.exec_driver_sql("SELECT current_database()").scalar()
        conn.exec_driver_sql(f'ALTER DATABASE "{dbname}" SET timezone TO \'Asia/Shanghai\'')
        # 顺带确认
        tz = conn.exec_driver_sql("SHOW timezone").scalar()
        print(f"[migrate] 数据库 {dbname!r} 时区已设为 Asia/Shanghai（当前 SHOW timezone = {tz}）")


if __name__ == "__main__":
    main()
