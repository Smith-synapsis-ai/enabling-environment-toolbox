from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://ee_user:ee_dev_password@localhost:5433/ee_toolbox"
    DATABASE_URL_SYNC: str = "postgresql://ee_user:ee_dev_password@localhost:5433/ee_toolbox"

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    CORS_ORIGINS: str = "*"
    DEFAULT_MODEL: str = "claude-sonnet-4-20250514"
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_MAX_TOKENS: int = 4096

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[2] / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
