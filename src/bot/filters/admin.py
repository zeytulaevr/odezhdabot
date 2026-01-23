"""Фильтры для проверки прав доступа."""

from aiogram.filters import BaseFilter
from aiogram.types import Message

from src.core.constants import UserRole
from src.database.models.user import User


class IsAdminFilter(BaseFilter):
    """Фильтр для проверки, является ли пользователь администратором."""

    async def __call__(self, message: Message, user: User | None = None) -> bool:
        """Проверка прав администратора.

        Args:
            message: Сообщение от пользователя
            user: Пользователь из БД (добавляется AuthMiddleware)

        Returns:
            True если пользователь администратор или супер-администратор
        """
        # Проверка по роли в БД
        if user and user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
            return True

        return False


class IsModeratorFilter(BaseFilter):
    """Фильтр для проверки, является ли пользователь модератором или администратором."""

    async def __call__(self, message: Message, user: User | None = None) -> bool:
        """Проверка прав модератора.

        Args:
            message: Сообщение от пользователя
            user: Пользователь из БД (добавляется AuthMiddleware)

        Returns:
            True если пользователь модератор, админ или супер-админ
        """
        # Проверка по роли в БД
        if user and user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value, UserRole.MODERATOR.value]:
            return True

        return False
