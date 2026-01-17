"""Middleware для работы с базой данных."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from src.database.base import async_session_maker
from src.database.repositories import OrderRepository, ProductRepository, UserRepository


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для добавления репозиториев в контекст обработчиков."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Добавление репозиториев в data.

        Args:
            handler: Следующий обработчик
            event: Событие от Telegram
            data: Данные для передачи в обработчик

        Returns:
            Результат выполнения обработчика
        """
        async with async_session_maker() as session:
            # Добавляем репозитории в контекст
            data["session"] = session
            data["user_repo"] = UserRepository(session)
            data["product_repo"] = ProductRepository(session)
            data["order_repo"] = OrderRepository(session)

            try:
                return await handler(event, data)
            except Exception as e:
                # Откат транзакции при ошибке
                await session.rollback()
                raise e
