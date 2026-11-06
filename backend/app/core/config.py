from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """全局配置，backend/.env 优先于默认值。"""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://root:root@localhost:5432/kaoyan"
    auth_username: str = "owner"
    auth_password: str = "kaoyan2026"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    exam_date: str = "2026-12-19"
    words_per_day: int = 50


settings = Settings()
