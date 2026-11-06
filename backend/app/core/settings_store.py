"""系统配置存取（system_settings 表）：LLM 网关等运行时可变配置。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.setting import SystemSetting

LLM_KEYS = ("llm_base_url", "llm_api_key", "llm_model")


def get_all(session: Session) -> dict[str, str]:
    rows = session.scalars(select(SystemSetting)).all()
    return {r.key: (r.value or "") for r in rows}


def get_llm_config(session: Session) -> dict[str, str]:
    d = get_all(session)
    return {k: d.get(k, "") for k in LLM_KEYS}


def set_many(session: Session, values: dict[str, str]) -> None:
    for k, v in values.items():
        row = session.get(SystemSetting, k)
        if row is None:
            session.add(SystemSetting(key=k, value=v or ""))
        else:
            row.value = v or ""
    session.commit()


def mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}***{key[-4:]}"
