"""Конфигурация приложения с использованием Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения с валидацией через Pydantic."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Отключаем автоматический парсинг JSON для env переменных
        env_parse_none_str="null",
    )

    # ========================================
    # TELEGRAM BOT CONFIGURATION
    # ========================================
    bot_token: str = Field(..., description="Токен Telegram бота от @BotFather")

    # Webhook настройки
    use_webhook: bool = Field(default=False, description="Использовать webhook вместо polling")
    webhook_url: str | None = Field(default=None, description="URL для webhook")
    webhook_path: str = Field(default="/webhook", description="Path для webhook")
    webapp_host: str = Field(default="0.0.0.0", description="Host для webhook сервера")
    webapp_port: int = Field(default=8080, description="Port для webhook сервера")

    # ========================================
    # DATABASE CONFIGURATION
    # ========================================
    postgres_host: str = Field(default="localhost", description="Хост PostgreSQL")
    postgres_port: int = Field(default=5432, description="Порт PostgreSQL")
    postgres_db: str = Field(default="telegram_bot", description="Имя базы данных")
    postgres_user: str = Field(default="botuser", description="Пользователь БД")
    postgres_password: str = Field(default="changeme", description="Пароль БД")

    # Pool settings
    db_pool_size: int = Field(default=10, description="Размер пула соединений")
    db_max_overflow: int = Field(default=20, description="Максимальное переполнение пула")
    db_pool_timeout: int = Field(default=30, description="Таймаут ожидания соединения")
    db_echo: bool = Field(default=False, description="Логировать SQL запросы")

    @property
    def database_url(self) -> str:
        """Сформировать URL для подключения к PostgreSQL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ========================================
    # REDIS CONFIGURATION
    # ========================================
    redis_host: str = Field(default="localhost", description="Хост Redis")
    redis_port: int = Field(default=6379, description="Порт Redis")
    redis_password: str = Field(default="changeme", description="Пароль Redis")
    redis_db: int = Field(default=0, description="Номер БД Redis")

    @property
    def redis_url(self) -> str:
        """Сформировать URL для подключения к Redis."""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ========================================
    # LOGGING CONFIGURATION
    # ========================================
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Уровень логирования"
    )
    log_format: Literal["json", "console"] = Field(
        default="console", description="Формат логов"
    )
    log_file_path: Path = Field(
        default=Path("logs/bot.log"), description="Путь к файлу логов"
    )
    log_max_bytes: int = Field(default=10485760, description="Максимальный размер файла лога")
    log_backup_count: int = Field(default=5, description="Количество файлов ротации")

    # ========================================
    # APPLICATION SETTINGS
    # ========================================
    environment: Literal["development", "production"] = Field(
        default="development", description="Окружение приложения"
    )
    timezone: str = Field(default="Europe/Moscow", description="Часовой пояс")
    default_language: str = Field(default="ru", description="Язык по умолчанию")

    @property
    def is_production(self) -> bool:
        """Проверка на продакшн окружение."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Проверка на development окружение."""
        return self.environment == "development"

    # ========================================
    # ADMIN SETTINGS
    # ========================================
    admin_ids: list[int] = Field(default_factory=list, description="ID администраторов")

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v) -> list[int]:
        """Парсинг ID администраторов из строки или списка."""
        if v is None or v == "":
            return []
        if isinstance(v, str):
            if not v.strip():
                return []
            # Парсим строку с запятыми
            return [int(id_str.strip()) for id_str in v.split(",") if id_str.strip()]
        if isinstance(v, list):
            return v
        # Если это одно число
        return [int(v)]

    # ========================================
    # PAYMENT SETTINGS
    # ========================================
    payment_token: str | None = Field(default=None, description="Токен платёжной системы")

    # ========================================
    # EXTERNAL APIs
    # ========================================
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN для мониторинга ошибок")
    amplitude_api_key: str | None = Field(default=None, description="Amplitude API ключ")

    # ========================================
    # FEATURE FLAGS
    # ========================================
    enable_payments: bool = Field(default=False, description="Включить платежи")
    enable_notifications: bool = Field(default=True, description="Включить уведомления")
    enable_analytics: bool = Field(default=False, description="Включить аналитику")

    # ========================================
    # RATE LIMITING
    # ========================================
    rate_limit_per_minute: int = Field(
        default=20, description="Лимит запросов на пользователя в минуту"
    )


@lru_cache
def get_settings() -> Settings:
    """Получить настройки приложения (singleton pattern)."""
    return Settings()


# Экспорт для удобного импорта
settings = get_settings()
