"""Глобальный обработчик ошибок."""

import traceback
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery, Message

from src.core.logging import get_logger
from src.utils.alerts import send_error_alert

logger = get_logger(__name__)


class ErrorHandler:
    """Обработчик ошибок с красивыми сообщениями для пользователей."""

    @staticmethod
    def get_user_friendly_message(error: Exception) -> str:
        """Получить понятное пользователю сообщение об ошибке.

        Args:
            error: Исключение

        Returns:
            Сообщение для пользователя
        """
        error_type = type(error).__name__

        # Специфичные сообщения для известных ошибок
        if isinstance(error, TelegramForbiddenError):
            return (
                "❌ У бота нет доступа для выполнения этого действия.\n\n"
                "Пожалуйста, проверьте права бота."
            )

        if isinstance(error, TelegramBadRequest):
            return (
                "❌ Некорректный запрос.\n\n"
                "Попробуйте повторить операцию или обратитесь к администратору."
            )

        if "Database" in error_type or "SQL" in error_type:
            return (
                "❌ Ошибка при работе с базой данных.\n\n"
                "Попробуйте повторить попытку через несколько секунд."
            )

        # Общее сообщение
        return (
            "❌ Произошла ошибка при выполнении операции.\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )

    @staticmethod
    async def handle_error(
        error: Exception,
        event: Message | CallbackQuery | None = None,
        bot: Bot | None = None,
        context: dict[str, Any] | None = None,
        send_to_user: bool = True,
    ) -> None:
        """Обработать ошибку.

        Args:
            error: Исключение
            event: Событие (Message или CallbackQuery)
            bot: Экземпляр бота
            context: Дополнительный контекст
            send_to_user: Отправить ли сообщение пользователю
        """
        error_type = type(error).__name__
        error_message = str(error)
        error_traceback = traceback.format_exc()

        # Формируем контекст для логов
        log_context = {
            "error_type": error_type,
            "error": error_message,
            **(context or {}),
        }

        if event:
            user = event.from_user if hasattr(event, "from_user") else None
            if user:
                log_context.update({
                    "user_id": user.id,
                    "username": user.username,
                    "full_name": user.full_name,
                })

            if isinstance(event, Message):
                log_context.update({
                    "message_id": event.message_id,
                    "chat_id": event.chat.id,
                    "text": event.text[:100] if event.text else None,
                })
            elif isinstance(event, CallbackQuery):
                log_context.update({
                    "callback_data": event.data,
                })

        # Логируем ошибку
        logger.error(
            "Error occurred",
            **log_context,
            exc_info=True,
        )

        # Отправляем алерт админам (если есть бот)
        if bot:
            await send_error_alert(
                bot=bot,
                error=error,
                context=log_context,
            )

        # Отправляем сообщение пользователю
        if send_to_user and event:
            user_message = ErrorHandler.get_user_friendly_message(error)

            try:
                if isinstance(event, Message):
                    await event.answer(user_message)
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        "Произошла ошибка. Попробуйте позже.",
                        show_alert=True,
                    )
                    if event.message:
                        await event.message.answer(user_message)
            except Exception as send_error:
                logger.warning(
                    "Failed to send error message to user",
                    error=str(send_error),
                )

    @staticmethod
    def get_short_traceback(error: Exception, max_lines: int = 5) -> str:
        """Получить короткий traceback для алертов.

        Args:
            error: Исключение
            max_lines: Максимум строк

        Returns:
            Короткий traceback
        """
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)

        # Берем последние строки
        relevant_lines = tb_lines[-max_lines:]

        return "".join(relevant_lines)


# Декоратор для обработки ошибок
def handle_errors(send_to_user: bool = True):
    """Декоратор для автоматической обработки ошибок в хендлерах.

    Args:
        send_to_user: Отправлять ли сообщение об ошибке пользователю

    Example:
        @handle_errors()
        async def my_handler(message: Message):
            # Ваш код
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Ищем event и bot в args/kwargs
                event = None
                bot = None

                for arg in args:
                    if isinstance(arg, (Message, CallbackQuery)):
                        event = arg
                        bot = arg.bot
                        break

                if not bot and "bot" in kwargs:
                    bot = kwargs["bot"]

                # Обрабатываем ошибку
                await ErrorHandler.handle_error(
                    error=e,
                    event=event,
                    bot=bot,
                    context={"handler": func.__name__},
                    send_to_user=send_to_user,
                )

                # Пробрасываем исключение дальше
                raise

        return wrapper
    return decorator
