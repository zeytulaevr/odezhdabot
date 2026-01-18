"""Middleware для авторизации и проверки пользователей."""

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update, User as TelegramUser

from src.core.constants import UserRole
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.user import UserRepository

logger = get_logger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware для регистрации и проверки пользователей."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Проверка и регистрация пользователя.

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

        # Формируем полное имя
        full_name = telegram_user.full_name or telegram_user.first_name

        # Получение или создание пользователя
        try:
            user, is_new = await user_repo.get_or_create(
                telegram_id=telegram_user.id,
                full_name=full_name,
                username=telegram_user.username,
            )

            if is_new:
                logger.info(
                    "New user registered",
                    user_id=user.id,
                    telegram_id=user.telegram_id,
                    username=user.username,
                    full_name=user.full_name,
                )

            # Проверка блокировки
            if user.is_banned:
                logger.warning("Banned user attempt", user_id=user.id, telegram_id=user.telegram_id)

                # Отправляем сообщение о блокировке
                if isinstance(event, Message):
                    await event.answer(
                        "🚫 <b>Доступ запрещён</b>\n\n"
                        "Ваш аккаунт заблокирован.\n"
                        "Для разблокировки обратитесь к администратору.",
                        parse_mode="HTML",
                    )
                return None

            # Добавляем пользователя в контекст
            data["user"] = user

        except Exception as e:
            logger.error(
                "Error in auth middleware",
                error=str(e),
                telegram_id=telegram_user.id,
                exc_info=True,
            )
            # Продолжаем выполнение даже при ошибке
            pass

        return await handler(event, data)


class RoleMiddleware(BaseMiddleware):
    """Middleware для проверки роли пользователя."""

    def __init__(self, required_role: str | None = None) -> None:
        """Инициализация middleware.

        Args:
            required_role: Требуемая роль ('admin', 'super_admin')
        """
        self.required_role = required_role

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Проверка роли пользователя.

        Args:
            handler: Следующий обработчик
            event: Событие от Telegram
            data: Данные для передачи в обработчик

        Returns:
            Результат выполнения обработчика
        """
        user: User | None = data.get("user")

        if not user:
            logger.warning("User not found in data for role check")
            return None

        # Если не требуется роль, пропускаем
        if not self.required_role:
            return await handler(event, data)

        # Проверка роли
        has_access = False

        if self.required_role == UserRole.ADMIN.value:
            has_access = user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]
        elif self.required_role == UserRole.SUPER_ADMIN.value:
            has_access = user.role == UserRole.SUPER_ADMIN.value

        if not has_access:
            logger.warning(
                "Access denied",
                user_id=user.id,
                user_role=user.role,
                required_role=self.required_role,
            )

            # Отправляем сообщение об отказе в доступе
            if isinstance(event, Message):
                await event.answer(
                    "🚫 <b>Доступ запрещён</b>\n\n"
                    "У вас нет прав для выполнения этой команды.",
                    parse_mode="HTML",
                )
            return None

        return await handler(event, data)
