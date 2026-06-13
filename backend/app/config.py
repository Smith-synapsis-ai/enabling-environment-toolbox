from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://ee_user:ee_dev_password@localhost:5433/ee_toolbox"
    DATABASE_URL_SYNC: str = "postgresql://ee_user:ee_dev_password@localhost:5433/ee_toolbox"

    ADMIN_USERNAME: str = "admin"
    # SECURITY: no usable default. The admin password MUST be supplied at runtime
    # via the ADMIN_PASSWORD env var (in production it is read from Secrets
    # Manager — ee-toolbox-api-keys — and exported by entrypoint.sh). If it is
    # left empty, or set to a known-insecure placeholder, admin login fails
    # CLOSED (see admin_password_is_secure() / admin_login). This prevents the
    # historical "admin/admin123" default from ever unlocking the admin surface.
    ADMIN_PASSWORD: str = ""
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


# Known-insecure placeholder values that must NEVER unlock the admin surface,
# even if they somehow end up in the environment. The app fails CLOSED on these.
_INSECURE_ADMIN_PASSWORDS = frozenset({"", "admin123", "admin", "password", "changeme"})


def admin_password_is_secure() -> bool:
    """True only when a real, non-placeholder admin password is configured.

    Fails CLOSED: an empty or known-insecure placeholder password means admin
    login is disabled entirely (returns 401) rather than accepting a weak
    default. In production the password is injected from Secrets Manager.
    """
    pw = (settings.ADMIN_PASSWORD or "").strip()
    if pw in _INSECURE_ADMIN_PASSWORDS:
        return False
    # Require minimal strength so a fat-fingered short value can't slip through.
    return len(pw) >= 12
