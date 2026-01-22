"""Система алертов и уведомлений для администраторов."""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from aiogram import Bot

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class AlertLevel(str, Enum):
    """Уровни алертов."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertManager:
    """Менеджер алертов для уведомления администраторов."""

    # Хранилище для подсчета ошибок (в памяти)
    _error_counts: dict[str, list[datetime]] = defaultdict(list)

    # Порог для алерта о массовых ошибках
    ERROR_THRESHOLD = 10
    ERROR_WINDOW = timedelta(minutes=1)

    @classmethod
    async def send_alert(
        cls,
        bot: Bot,
        level: AlertLevel,
        message: str,
        details: dict[str, Any] | None = None,
        notify_all: bool = False,
    ) -> None:
        """Отправить алерт администраторам.

        Args:
            bot: Экземпляр бота
            level: Уровень алерта
            message: Сообщение алерта
            details: Дополнительные детали
            notify_all: Уведомить всех админов (иначе только super_admin)
        """
        # Эмодзи для уровней
        level_emoji = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.ERROR: "❌",
            AlertLevel.CRITICAL: "🚨",
        }

        emoji = level_emoji.get(level, "📢")
        level_text = level.value.upper()

        # Форматируем сообщение
        text = f"{emoji} <b>{level_text} ALERT</b>\n\n{message}"

        if details:
            text += "\n\n<b>Details:</b>\n"
            for key, value in details.items():
                # Ограничение длины значений
                value_str = str(value)
                if len(value_str) > 200:
                    value_str = value_str[:197] + "..."
                text += f"• {key}: <code>{value_str}</code>\n"

        text += f"\n⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

        # Определяем получателей
        if level == AlertLevel.CRITICAL or notify_all:
            # Критические алерты всем super_admin
            recipients = settings.superadmin_ids
        else:
            # Обычные алерты только первому super_admin
            recipients = [settings.superadmin_ids[0]] if settings.superadmin_ids else []

        # Отправка асинхронно
        tasks = []
        for admin_id in recipients:
            task = cls._send_to_admin(bot, admin_id, text)
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(
            "Alert sent",
            level=level.value,
            message=message,
            recipients=len(recipients),
        )

    @staticmethod
    async def _send_to_admin(bot: Bot, admin_id: int, text: str) -> None:
        """Отправить сообщение конкретному админу.

        Args:
            bot: Экземпляр бота
            admin_id: Telegram ID админа
            text: Текст сообщения
        """
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(
                "Failed to send alert to admin",
                admin_id=admin_id,
                error=str(e),
            )

    @classmethod
    async def track_error(
        cls,
        bot: Bot,
        error_type: str,
        error_message: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Отслеживать ошибки и отправлять алерты при превышении порога.

        Args:
            bot: Экземпляр бота
            error_type: Тип ошибки
            error_message: Сообщение об ошибке
            context: Контекст ошибки
        """
        now = datetime.utcnow()

        # Добавляем ошибку в счетчик
        cls._error_counts[error_type].append(now)

        # Очищаем старые записи (вне окна)
        cutoff = now - cls.ERROR_WINDOW
        cls._error_counts[error_type] = [
            ts for ts in cls._error_counts[error_type] if ts > cutoff
        ]

        # Проверяем порог
        error_count = len(cls._error_counts[error_type])

        if error_count >= cls.ERROR_THRESHOLD:
            # Отправляем критический алерт
            await cls.send_alert(
                bot=bot,
                level=AlertLevel.CRITICAL,
                message=f"⚠️ Множественные ошибки: {error_type}",
                details={
                    "error_count": error_count,
                    "time_window": f"{cls.ERROR_WINDOW.seconds}s",
                    "error_message": error_message,
                    **(context or {}),
                },
                notify_all=True,
            )

            # Очищаем счетчик после алерта
            cls._error_counts[error_type] = []

            logger.critical(
                "Mass error alert sent",
                error_type=error_type,
                count=error_count,
            )

    @staticmethod
    async def send_error_alert(
        bot: Bot,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Отправить алерт об ошибке.

        Args:
            bot: Экземпляр бота
            error: Исключение
            context: Контекст ошибки
        """
        error_type = type(error).__name__
        error_message = str(error)

        await AlertManager.send_alert(
            bot=bot,
            level=AlertLevel.ERROR,
            message=f"Exception: {error_type}",
            details={
                "error": error_message,
                "type": error_type,
                **(context or {}),
            },
        )

        # Трекинг для массовых ошибок
        await AlertManager.track_error(bot, error_type, error_message, context)

    @staticmethod
    async def send_warning_alert(
        bot: Bot,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Отправить предупреждающий алерт.

        Args:
            bot: Экземпляр бота
            message: Сообщение
            details: Детали
        """
        await AlertManager.send_alert(
            bot=bot,
            level=AlertLevel.WARNING,
            message=message,
            details=details,
        )

    @staticmethod
    async def send_info_alert(
        bot: Bot,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Отправить информационный алерт.

        Args:
            bot: Экземпляр бота
            message: Сообщение
            details: Детали
        """
        await AlertManager.send_alert(
            bot=bot,
            level=AlertLevel.INFO,
            message=message,
            details=details,
        )

    @staticmethod
    async def send_critical_alert(
        bot: Bot,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Отправить критический алерт всем super_admin.

        Args:
            bot: Экземпляр бота
            message: Сообщение
            details: Детали
        """
        await AlertManager.send_alert(
            bot=bot,
            level=AlertLevel.CRITICAL,
            message=message,
            details=details,
            notify_all=True,
        )


# Alias для удобства
send_alert = AlertManager.send_alert
send_error_alert = AlertManager.send_error_alert
send_warning_alert = AlertManager.send_warning_alert
send_info_alert = AlertManager.send_info_alert
send_critical_alert = AlertManager.send_critical_alert
