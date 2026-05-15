from __future__ import annotations

from functools import lru_cache
from os import getenv

from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "sqlite+pysqlite:///:memory:"
    app_secret_key: str = "dev-secret-change-me"
    app_base_url: str = "http://localhost:8000"
    admin_username: str = "admin"
    admin_initial_password: str | None = None
    session_cookie_secure: bool = False
    mcp_enabled: bool = True
    log_level: str = "INFO"


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=getenv("DATABASE_URL", Settings().database_url),
        app_secret_key=getenv("APP_SECRET_KEY", Settings().app_secret_key),
        app_base_url=getenv("APP_BASE_URL", Settings().app_base_url),
        admin_username=getenv("ADMIN_USERNAME", Settings().admin_username),
        admin_initial_password=getenv("ADMIN_INITIAL_PASSWORD") or None,
        session_cookie_secure=_as_bool(getenv("SESSION_COOKIE_SECURE"), False),
        mcp_enabled=_as_bool(getenv("MCP_ENABLED"), True),
        log_level=getenv("LOG_LEVEL", Settings().log_level),
    )
