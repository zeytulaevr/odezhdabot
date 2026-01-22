"""Middleware для логирования событий."""

import re
import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Contact, Message, TelegramObject, Update

from src.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования входящих событий и времени обработки."""

    # Паттерны для маскировки чувствительных данных
    PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}')
    EMAIL_PATTERN = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')

    @staticmethod
    def mask_sensitive_data(text: str | None) -> str | None:
        """Маскировать чувствительные данные в тексте.

        Args:
            text: Исходный текст

        Returns:
            Текст с замаскированными данными
        """
        if not text:
            return text

        # Маскируем телефоны (оставляем последние 2 цифры)
        text = LoggingMiddleware.PHONE_PATTERN.sub(
            lambda m: m.group()[:-2] + "**", text
        )

        # Маскируем email (оставляем первую букву и домен)
        text = LoggingMiddleware.EMAIL_PATTERN.sub(
            lambda m: m.group()[0] + "***@" + m.group().split("@")[1], text
        )

        return text

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Логирование события и времени обработки.

        Args:
            handler: Следующий обработчик
            event: Событие от Telegram
            data: Данные для передачи в обработчик

        Returns:
            Результат выполнения обработчика
        """
        start_time = time.time()

        # Определение типа события и извлечение информации
        event_type = type(event).__name__
        user = None
        event_info: dict[str, Any] = {"event_type": event_type}

        if isinstance(event, Message):
            user = event.from_user

            # Маскируем текст сообщения
            text = event.text
            if text:
                text = self.mask_sensitive_data(text[:100])  # Первые 100 символов

            event_info.update({
                "message_id": event.message_id,
                "chat_id": event.chat.id,
                "text": text,
            })

            # Логируем тип контента (без самого контента)
            if event.photo:
                event_info["content_type"] = "photo"
            elif event.video:
                event_info["content_type"] = "video"
            elif event.document:
                event_info["content_type"] = "document"
            elif event.contact:
                event_info["content_type"] = "contact"
                # НЕ логируем сам контакт

        elif isinstance(event, CallbackQuery):
            user = event.from_user
            event_info.update({
                "callback_data": event.data,
                "message_id": event.message.message_id if event.message else None,
            })

        if user:
            event_info.update({
                "user_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
            })

        logger.info("Incoming event", **event_info)

        try:
            result = await handler(event, data)

            # Время обработки
            processing_time = time.time() - start_time
            logger.info(
                "Event processed successfully",
                processing_time=f"{processing_time:.3f}s",
                **event_info,
            )

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Error processing event",
                error=str(e),
                error_type=type(e).__name__,
                processing_time=f"{processing_time:.3f}s",
                **event_info,
                exc_info=True,
            )

            # Отправляем алерт если есть бот
            if hasattr(event, "bot"):
                from src.utils.error_handler import ErrorHandler
                await ErrorHandler.handle_error(
                    error=e,
                    event=event if isinstance(event, (Message, CallbackQuery)) else None,
                    bot=event.bot,
                    context=event_info,
                    send_to_user=False,  # Не отправляем пользователю из middleware
                )

            raise
