from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from aiogram.exceptions import TelegramBadRequest


class Settings(BaseSettings):
    """Настройки приложения с валидацией через Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_parse_none_str="null",
    )

    # ===============================
    # TELEGRAM BOT CONFIG
    # ===============================
    bot_token: str = Field(..., description="Токен Telegram бота")
    use_webhook: bool = Field(default=False)
    webhook_url: str | None = None
    webhook_path: str = "/webhook"
    webapp_host: str = "0.0.0.0"
    webapp_port: int = 8080

    # ===============================
    # DATABASE CONFIG
    # ===============================
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "telegram_bot"
    postgres_user: str = "botuser"
    postgres_password: str = "changeme"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_echo: bool = False

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # ===============================
    # REDIS CONFIG
    # ===============================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = "changeme"
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ===============================
    # LOGGING CONFIG
    # ===============================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "console"
    log_file_path: Path = Path("logs/bot.log")
    log_max_bytes: int = 10485760
    log_backup_count: int = 5

    # ===============================
    # APPLICATION SETTINGS
    # ===============================
    environment: Literal["development", "production"] = "development"
    timezone: str = "Europe/Moscow"
    default_language: str = "ru"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    # ===============================
    # ADMIN SETTINGS
    # ===============================
    superadmin_ids: list[int] = Field(default_factory=list, description="ID супер-администраторов")

    @field_validator("superadmin_ids", mode="before")
    @classmethod
    def parse_superadmin_ids(cls, v) -> list[int]:
        if not v:
            return []
        if isinstance(v, str):
            return [int(i.strip()) for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        return [int(v)]

    # ===============================
    # CHANNEL SETTINGS
    # ===============================
    channel_id: int | None = None
    review_channel_id: int | None = None

    # ===============================
    # PAYMENT SETTINGS
    # ===============================
    payment_token: str | None = None

    # ===============================
    # EXTERNAL APIs
    # ===============================
    sentry_dsn: str | None = None
    amplitude_api_key: str | None = None

    # ===============================
    # FEATURE FLAGS
    # ===============================
    enable_payments: bool = False
    enable_notifications: bool = True
    enable_analytics: bool = False

    # ===============================
    # RATE LIMITING
    # ===============================
    rate_limit_per_minute: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
