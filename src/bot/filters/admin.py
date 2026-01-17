"""Фильтры для проверки прав доступа."""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from src.core.config import settings
from src.core.constants import UserRole
from src.database.models.user import User


class IsAdminFilter(BaseFilter):
    """Фильтр для проверки, является ли пользователь администратором."""

    async def __call__(self, message: Message, db_user: User | None = None) -> bool:
        """Проверка прав администратора.

        Args:
            message: Сообщение от пользователя
            db_user: Пользователь из БД (добавляется UserMiddleware)

        Returns:
            True если пользователь администратор
        """
        # Проверка по списку админов из конфига
        if message.from_user.id in settings.admin_ids:
            return True

        # Проверка по роли в БД
        if db_user and db_user.role == UserRole.ADMIN.value:
            return True

        return False


class IsModeratorFilter(BaseFilter):
    """Фильтр для проверки, является ли пользователь модератором или администратором."""

    async def __call__(self, message: Message, db_user: User | None = None) -> bool:
        """Проверка прав модератора.

        Args:
            message: Сообщение от пользователя
            db_user: Пользователь из БД

        Returns:
            True если пользователь модератор или админ
        """
        # Проверка по списку админов
        if message.from_user.id in settings.admin_ids:
            return True

        # Проверка по роли в БД
        if db_user and db_user.role in [UserRole.ADMIN.value, UserRole.MODERATOR.value]:
            return True

        return False
