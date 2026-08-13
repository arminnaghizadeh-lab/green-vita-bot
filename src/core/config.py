"""
Centralized application configuration.

همه‌ی تنظیمات پروژه از اینجا خوانده می‌شود. هیچ جای دیگری از کد نباید
مستقیم os.environ را بخواند — همه چیز باید از طریق get_settings() عبور کند.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- App ----------
    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "Green Vita AI Plant Clinic"
    debug: bool = True
    secret_key: str = "insecure-dev-key-change-me"
    timezone: str = "Asia/Tehran"

    # ---------- Telegram ----------
    bot_token: str = ""
    bot_admin_ids: str = ""  # comma separated, parsed via property

    # ---------- Database ----------
    database_url: str = "sqlite+aiosqlite:///./greenvita.db"
    postgres_user: str = "greenvita"
    postgres_password: str = "greenvita"
    postgres_db: str = "greenvita"
    postgres_host: str = "db"
    postgres_port: int = 5432

    # ---------- Redis ----------
    redis_url: str = "redis://localhost:6379/0"

    # ---------- AI Provider ----------
    ai_provider: Literal["claude", "gemini", "openai"] = "claude"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    # برای gatewayهای سازگار با OpenAI (مثل AvalAI/GapGPT) که مدل‌های غیر-OpenAI
    # (مثل Claude) رو هم از پشت همین فرمت ارائه می‌دن. خالی = آدرس رسمی OpenAI.
    openai_base_url: str = ""

    # ---------- Admin panel ----------
    admin_username: str = "admin"
    admin_password: str = "admin"
    admin_session_secret: str = "insecure-session-secret-change-me"
    admin_port: int = 8000

    # ---------- Logging ----------
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        # پشتیبانی از هر دو حالت sync/async پیشوند pg، فقط برای اطمینان
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @property
    def admin_ids(self) -> list[int]:
        if not self.bot_admin_ids:
            return []
        return [int(x.strip()) for x in self.bot_admin_ids.split(",") if x.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — تنظیمات فقط یک بار خوانده و کش می‌شود."""
    return Settings()
