"""Shared configuration for the EE Toolbox pipeline.

All values are read from environment variables with sensible local-dev defaults.
"""

import os

# Database connection strings
DATABASE_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://ee_user:ee_dev_password@localhost:5433/ee_toolbox",
)
DATABASE_URL_ASYNC = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://ee_user:ee_dev_password@localhost:5433/ee_toolbox",
)

# LLM settings
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_TIMEOUT_SECONDS = int(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))
