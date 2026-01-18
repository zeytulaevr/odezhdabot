"""Репозиторий для работы с модерируемыми сообщениями."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.moderated_message import ModeratedMessage
from src.database.repositories.base import BaseRepository


class ModeratedMessageRepository(BaseRepository[ModeratedMessage]):
    """Репозиторий для работы с модерируемыми сообщениями."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория модерируемых сообщений."""
        super().__init__(ModeratedMessage, session)

    async def get_pending(self, limit: int = 50) -> list[ModeratedMessage]:
        """Получить сообщения, ожидающие модерации.

        Args:
            limit: Максимальное количество сообщений

        Returns:
            Список сообщений на модерации
        """
        stmt = (
            select(ModeratedMessage)
            .where(ModeratedMessage.status == "pending")
            .order_by(ModeratedMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_message_id(
        self, message_id: int, chat_id: int
    ) -> ModeratedMessage | None:
        """Получить запись по ID сообщения.

        Args:
            message_id: Telegram ID сообщения
            chat_id: Telegram ID чата

        Returns:
            Запись модерации или None
        """
        stmt = select(ModeratedMessage).where(
            ModeratedMessage.message_id == message_id,
            ModeratedMessage.chat_id == chat_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_recent_messages(
        self, user_id: int, hours: int = 24, limit: int = 10
    ) -> list[ModeratedMessage]:
        """Получить последние сообщения пользователя.

        Args:
            user_id: ID пользователя
            hours: За сколько часов искать
            limit: Максимальное количество

        Returns:
            Список сообщений пользователя
        """
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        stmt = (
            select(ModeratedMessage)
            .where(
                ModeratedMessage.user_id == user_id,
                ModeratedMessage.created_at >= cutoff_time,
            )
            .order_by(ModeratedMessage.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def approve_message(
        self, message_id: int, moderator_id: int | None = None, comment: str | None = None
    ) -> ModeratedMessage | None:
        """Одобрить сообщение.

        Args:
            message_id: ID записи
            moderator_id: ID модератора
            comment: Комментарий

        Returns:
            Обновленная запись или None
        """
        message = await self.get(message_id)
        if not message:
            return None

        message.status = "approved"
        message.moderator_id = moderator_id
        message.moderator_comment = comment
        message.moderated_at = datetime.utcnow()

        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def reject_message(
        self,
        message_id: int,
        moderator_id: int | None = None,
        comment: str | None = None,
        mark_deleted: bool = True,
    ) -> ModeratedMessage | None:
        """Отклонить сообщение.

        Args:
            message_id: ID записи
            moderator_id: ID модератора
            comment: Комментарий
            mark_deleted: Пометить как удаленное

        Returns:
            Обновленная запись или None
        """
        message = await self.get(message_id)
        if not message:
            return None

        message.status = "rejected"
        message.moderator_id = moderator_id
        message.moderator_comment = comment
        message.moderated_at = datetime.utcnow()
        if mark_deleted:
            message.is_deleted = True

        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_spam_statistics(self, days: int = 7) -> dict:
        """Получить статистику по спаму за период.

        Args:
            days: Количество дней

        Returns:
            Словарь со статистикой
        """
        from datetime import timedelta
        from sqlalchemy import func

        cutoff_time = datetime.utcnow() - timedelta(days=days)

        # Общее количество
        total_stmt = select(func.count()).select_from(ModeratedMessage).where(
            ModeratedMessage.created_at >= cutoff_time
        )
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar() or 0

        # Одобренные
        approved_stmt = (
            select(func.count())
            .select_from(ModeratedMessage)
            .where(
                ModeratedMessage.created_at >= cutoff_time,
                ModeratedMessage.status.in_(["approved", "auto_approved"]),
            )
        )
        approved_result = await self.session.execute(approved_stmt)
        approved = approved_result.scalar() or 0

        # Отклоненные
        rejected_stmt = (
            select(func.count())
            .select_from(ModeratedMessage)
            .where(
                ModeratedMessage.created_at >= cutoff_time,
                ModeratedMessage.status.in_(["rejected", "auto_rejected"]),
            )
        )
        rejected_result = await self.session.execute(rejected_stmt)
        rejected = rejected_result.scalar() or 0

        # Ожидающие
        pending_stmt = (
            select(func.count())
            .select_from(ModeratedMessage)
            .where(
                ModeratedMessage.created_at >= cutoff_time,
                ModeratedMessage.status == "pending",
            )
        )
        pending_result = await self.session.execute(pending_stmt)
        pending = pending_result.scalar() or 0

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
        }
