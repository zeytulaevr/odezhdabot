"""Настройка логирования с использованием structlog."""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from src.core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Добавление контекста приложения к логам."""
    event_dict["environment"] = settings.environment
    event_dict["service"] = "telegram-bot"
    return event_dict


def setup_logging() -> None:
    """Настройка логирования для приложения."""
    # Создание директории для логов
    log_dir = settings.log_file_path.parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Общие процессоры для structlog
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Настройка рендерера в зависимости от формата
    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(
            colors=True if not settings.is_production else False
        )

    # Настройка structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Настройка стандартного logging
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    # Handler для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(settings.log_level)

    # Handler для записи в файл (с ротацией)
    from logging.handlers import RotatingFileHandler

    file_handler = RotatingFileHandler(
        filename=settings.log_file_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(settings.log_level)

    # Настройка root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.setLevel(settings.log_level)

    # Отключение избыточного логирования от сторонних библиотек
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """Получить logger с указанным именем."""
    return structlog.get_logger(name)
