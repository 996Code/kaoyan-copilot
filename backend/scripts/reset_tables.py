"""危险操作：清空并重建全部表。python -I scripts/reset_tables.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import engine  # noqa: E402
from app.models import Base  # noqa: E402


def main() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("all tables dropped & recreated")


if __name__ == "__main__":
    main()
