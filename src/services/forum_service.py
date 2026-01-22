"""Сервис для работы с темами форума Telegram."""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from src.core.logging import get_logger

logger = get_logger(__name__)


class ForumService:
    """Сервис для управления темами форума."""

    # Цвета иконок для тем (доступные в Telegram)
    ICON_COLORS = {
        "blue": 0x6FB9F0,
        "yellow": 0xFFD67E,
        "purple": 0xCB86DB,
        "green": 0x8EEE98,
        "pink": 0xFF93B2,
        "red": 0xFB6F5F,
    }

    @staticmethod
    async def create_forum_topic(
        bot: Bot,
        chat_id: int,
        name: str,
        icon_color: str = "blue",
        icon_custom_emoji_id: str | None = None,
    ) -> int | None:
        """Создать новую тему в форуме.

        Args:
            bot: Telegram Bot instance
            chat_id: ID чата-форума (должен быть супергруппой с включенными темами)
            name: Название темы
            icon_color: Цвет иконки (blue, yellow, purple, green, pink, red)
            icon_custom_emoji_id: ID кастомного эмодзи для иконки (опционально)

        Returns:
            message_thread_id новой темы или None при ошибке
        """
        try:
            # Получаем цвет из словаря
            color = ForumService.ICON_COLORS.get(icon_color, ForumService.ICON_COLORS["blue"])

            # Создаем тему
            result = await bot.create_forum_topic(
                chat_id=chat_id,
                name=name,
                icon_color=color,
                icon_custom_emoji_id=icon_custom_emoji_id,
            )

            logger.info(
                "Forum topic created",
                chat_id=chat_id,
                topic_name=name,
                thread_id=result.message_thread_id,
            )

            return result.message_thread_id

        except TelegramBadRequest as e:
            logger.error(
                "Failed to create forum topic",
                chat_id=chat_id,
                topic_name=name,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "Unexpected error creating forum topic",
                chat_id=chat_id,
                topic_name=name,
                error=str(e),
            )
            return None

    @staticmethod
    async def edit_forum_topic(
        bot: Bot,
        chat_id: int,
        message_thread_id: int,
        name: str | None = None,
        icon_custom_emoji_id: str | None = None,
    ) -> bool:
        """Редактировать существующую тему форума.

        Args:
            bot: Telegram Bot instance
            chat_id: ID чата-форума
            message_thread_id: ID темы
            name: Новое название темы (опционально)
            icon_custom_emoji_id: Новая иконка (опционально)

        Returns:
            True при успехе, False при ошибке
        """
        try:
            await bot.edit_forum_topic(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
                name=name,
                icon_custom_emoji_id=icon_custom_emoji_id,
            )

            logger.info(
                "Forum topic edited",
                chat_id=chat_id,
                thread_id=message_thread_id,
                new_name=name,
            )

            return True

        except TelegramBadRequest as e:
            logger.error(
                "Failed to edit forum topic",
                chat_id=chat_id,
                thread_id=message_thread_id,
                error=str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error editing forum topic",
                chat_id=chat_id,
                thread_id=message_thread_id,
                error=str(e),
            )
            return False

    @staticmethod
    async def delete_forum_topic(
        bot: Bot,
        chat_id: int,
        message_thread_id: int,
    ) -> bool:
        """Удалить тему форума.

        Args:
            bot: Telegram Bot instance
            chat_id: ID чата-форума
            message_thread_id: ID темы

        Returns:
            True при успехе, False при ошибке
        """
        try:
            await bot.delete_forum_topic(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
            )

            logger.info(
                "Forum topic deleted",
                chat_id=chat_id,
                thread_id=message_thread_id,
            )

            return True

        except TelegramBadRequest as e:
            logger.error(
                "Failed to delete forum topic",
                chat_id=chat_id,
                thread_id=message_thread_id,
                error=str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "Unexpected error deleting forum topic",
                chat_id=chat_id,
                thread_id=message_thread_id,
                error=str(e),
            )
            return False

    @staticmethod
    async def close_forum_topic(
        bot: Bot,
        chat_id: int,
        message_thread_id: int,
    ) -> bool:
        """Закрыть тему форума (запретить писать обычным пользователям).

        Args:
            bot: Telegram Bot instance
            chat_id: ID чата-форума
            message_thread_id: ID темы

        Returns:
            True при успехе, False при ошибке
        """
        try:
            await bot.close_forum_topic(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
            )

            logger.info(
                "Forum topic closed",
                chat_id=chat_id,
                thread_id=message_thread_id,
            )

            return True

        except TelegramBadRequest as e:
            logger.error(
                "Failed to close forum topic",
                chat_id=chat_id,
                thread_id=message_thread_id,
                error=str(e),
            )
            return False

    @staticmethod
    async def reopen_forum_topic(
        bot: Bot,
        chat_id: int,
        message_thread_id: int,
    ) -> bool:
        """Открыть тему форума (разрешить писать всем).

        Args:
            bot: Telegram Bot instance
            chat_id: ID чата-форума
            message_thread_id: ID темы

        Returns:
            True при успехе, False при ошибке
        """
        try:
            await bot.reopen_forum_topic(
                chat_id=chat_id,
                message_thread_id=message_thread_id,
            )

            logger.info(
                "Forum topic reopened",
                chat_id=chat_id,
                thread_id=message_thread_id,
            )

            return True

        except TelegramBadRequest as e:
            logger.error(
                "Failed to reopen forum topic",
                chat_id=chat_id,
                thread_id=message_thread_id,
                error=str(e),
            )
            return False
