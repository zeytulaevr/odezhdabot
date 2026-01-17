"""Middleware для логирования событий."""

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from src.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логирования входящих событий и времени обработки."""

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
            event_info.update({
                "message_id": event.message_id,
                "chat_id": event.chat.id,
                "text": event.text[:100] if event.text else None,  # Первые 100 символов
            })
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
            raise
