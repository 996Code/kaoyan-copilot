"""建表：python -I scripts/create_tables.py（在 backend 目录下运行）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import engine  # noqa: E402
from app.models import Base  # noqa: E402


def main() -> None:
    Base.metadata.create_all(engine)
    print("tables created:")
    for name in sorted(Base.metadata.tables):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
