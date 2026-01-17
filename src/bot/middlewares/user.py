"""Middleware для работы с пользователями."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, User as TelegramUser

from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories import UserRepository

logger = get_logger(__name__)


class UserMiddleware(BaseMiddleware):
    """Middleware для автоматической регистрации/обновления пользователей."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Регистрация или обновление пользователя в БД.

        Args:
            handler: Следующий обработчик
            event: Событие от Telegram
            data: Данные для передачи в обработчик

        Returns:
            Результат выполнения обработчика
        """
        # Получаем Telegram user из события
        telegram_user: TelegramUser | None = data.get("event_from_user")

        if not telegram_user:
            return await handler(event, data)

        # Получаем репозиторий пользователей
        user_repo: UserRepository = data.get("user_repo")

        if not user_repo:
            logger.warning("UserRepository not found in data")
            return await handler(event, data)

        # Получение или создание пользователя
        user, is_new = await user_repo.get_or_create(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        )

        if is_new:
            logger.info(
                "New user registered",
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
            )

        # Проверка блокировки
        if user.is_blocked:
            logger.warning("Blocked user attempt", user_id=user.id)
            # Можно отправить сообщение о блокировке
            return None

        # Добавляем пользователя в контекст
        data["db_user"] = user

        return await handler(event, data)
