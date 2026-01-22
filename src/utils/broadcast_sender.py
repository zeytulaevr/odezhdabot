"""Утилита для отправки массовых рассылок с rate limiting."""

import asyncio
from typing import Any

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.broadcast import Broadcast
from src.database.models.user import User
from src.services.broadcast_service import BroadcastService

logger = get_logger(__name__)


class BroadcastSender:
    """Класс для отправки рассылок с rate limiting."""

    # Telegram limits: 30 messages per second to different users
    # Используем более консервативный лимит для безопасности
    MESSAGES_PER_SECOND = 20
    BATCH_SIZE = 20
    BATCH_DELAY = 1.0  # секунд между батчами

    def __init__(
        self,
        bot: Bot,
        session: AsyncSession,
        broadcast_id: int,
    ):
        """Инициализация отправщика.

        Args:
            bot: Экземпляр бота
            session: Сессия БД
            broadcast_id: ID рассылки
        """
        self.bot = bot
        self.session = session
        self.broadcast_id = broadcast_id
        self.service = BroadcastService(session)

        # Счетчики
        self.sent_count = 0
        self.success_count = 0
        self.failed_count = 0

        # Флаг отмены
        self.cancelled = False

    async def send_broadcast(
        self,
        admin_telegram_id: int | None = None,
    ) -> dict[str, int]:
        """Отправить рассылку всем целевым пользователям.

        Args:
            admin_telegram_id: Telegram ID админа для прогресс-бара

        Returns:
            Словарь со статистикой отправки
        """
        # Получаем рассылку
        broadcast = await self.service.get_broadcast(self.broadcast_id)
        if not broadcast:
            logger.error(f"Broadcast {self.broadcast_id} not found")
            return {"error": "Broadcast not found"}

        if broadcast.status != "pending":
            logger.error(f"Broadcast {self.broadcast_id} has invalid status: {broadcast.status}")
            return {"error": "Invalid broadcast status"}

        # Обновляем статус на "in_progress"
        await self.service.update_broadcast_status(self.broadcast_id, "in_progress")
        await self.session.commit()

        logger.info(
            "Starting broadcast",
            broadcast_id=self.broadcast_id,
            total_target=broadcast.total_target,
        )

        # Получаем целевых пользователей
        target_users = await self.service.get_target_users(broadcast.filters or {})

        if not target_users:
            await self.service.update_broadcast_status(self.broadcast_id, "completed")
            await self.session.commit()
            logger.warning(f"No target users for broadcast {self.broadcast_id}")
            return {"sent": 0, "success": 0, "failed": 0}

        total_users = len(target_users)

        # Прогресс-бар для админа
        progress_message = None
        if admin_telegram_id:
            try:
                progress_message = await self.bot.send_message(
                    chat_id=admin_telegram_id,
                    text=f"📤 <b>Начинаем рассылку #{self.broadcast_id}</b>\n\n"
                    f"Получателей: {total_users}\n"
                    f"Прогресс: 0/{total_users} (0%)",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Failed to send progress message: {e}")

        # Отправка батчами
        for i in range(0, total_users, self.BATCH_SIZE):
            if self.cancelled:
                logger.info(f"Broadcast {self.broadcast_id} cancelled by admin")
                break

            batch = target_users[i : i + self.BATCH_SIZE]

            # Отправка батча параллельно
            tasks = [self._send_to_user(broadcast, user) for user in batch]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Обновляем прогресс
            progress = min(i + self.BATCH_SIZE, total_users)
            percentage = int((progress / total_users) * 100)

            # Обновляем статистику в БД
            await self.service.update_broadcast_stats(
                self.broadcast_id,
                sent_count=self.sent_count,
                success_count=self.success_count,
                failed_count=self.failed_count,
            )
            await self.session.commit()

            # Обновляем прогресс-бар
            if progress_message and progress % 100 == 0:  # Каждые 100 сообщений
                try:
                    await progress_message.edit_text(
                        text=f"📤 <b>Рассылка #{self.broadcast_id}</b>\n\n"
                        f"Получателей: {total_users}\n"
                        f"Прогресс: {progress}/{total_users} ({percentage}%)\n\n"
                        f"✅ Успешно: {self.success_count}\n"
                        f"❌ Ошибки: {self.failed_count}",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning(f"Failed to update progress message: {e}")

            # Задержка между батчами
            if i + self.BATCH_SIZE < total_users:
                await asyncio.sleep(self.BATCH_DELAY)

        # Финальное обновление статуса
        final_status = "cancelled" if self.cancelled else "completed"
        await self.service.update_broadcast_status(self.broadcast_id, final_status)
        await self.service.update_broadcast_stats(
            self.broadcast_id,
            sent_count=self.sent_count,
            success_count=self.success_count,
            failed_count=self.failed_count,
        )
        await self.session.commit()

        # Финальный прогресс-бар
        if progress_message:
            try:
                status_emoji = "✅" if final_status == "completed" else "🚫"
                await progress_message.edit_text(
                    text=f"{status_emoji} <b>Рассылка #{self.broadcast_id} завершена</b>\n\n"
                    f"Получателей: {total_users}\n"
                    f"Отправлено: {self.sent_count}\n\n"
                    f"✅ Успешно: {self.success_count}\n"
                    f"❌ Ошибки: {self.failed_count}\n\n"
                    f"Процент успеха: {int((self.success_count / total_users) * 100) if total_users > 0 else 0}%",
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Failed to update final progress message: {e}")

        logger.info(
            "Broadcast completed",
            broadcast_id=self.broadcast_id,
            sent=self.sent_count,
            success=self.success_count,
            failed=self.failed_count,
        )

        return {
            "sent": self.sent_count,
            "success": self.success_count,
            "failed": self.failed_count,
        }

    async def _send_to_user(self, broadcast: Broadcast, user: User) -> bool:
        """Отправить сообщение одному пользователю.

        Args:
            broadcast: Рассылка
            user: Пользователь

        Returns:
            True если успешно, False если ошибка
        """
        try:
            # Подготовка клавиатуры
            reply_markup = None
            if broadcast.buttons:
                reply_markup = self._build_keyboard(broadcast.buttons)

            # Отправка в зависимости от типа медиа
            if broadcast.media_type == "photo":
                await self.bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=broadcast.media_file_id,
                    caption=broadcast.text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            elif broadcast.media_type == "video":
                await self.bot.send_video(
                    chat_id=user.telegram_id,
                    video=broadcast.media_file_id,
                    caption=broadcast.text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            elif broadcast.media_type == "document":
                await self.bot.send_document(
                    chat_id=user.telegram_id,
                    document=broadcast.media_file_id,
                    caption=broadcast.text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            else:
                # Обычное текстовое сообщение
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=broadcast.text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )

            self.sent_count += 1
            self.success_count += 1
            return True

        except TelegramForbiddenError:
            # Пользователь заблокировал бота
            logger.info(f"User {user.id} blocked bot")
            self.sent_count += 1
            self.failed_count += 1
            await self.service.add_broadcast_error(
                self.broadcast_id,
                user.id,
                "User blocked bot",
            )
            return False

        except TelegramBadRequest as e:
            # Некорректный запрос (например, чат не найден)
            logger.warning(f"Bad request for user {user.id}: {e}")
            self.sent_count += 1
            self.failed_count += 1
            await self.service.add_broadcast_error(
                self.broadcast_id,
                user.id,
                f"Bad request: {str(e)}",
            )
            return False

        except TelegramRetryAfter as e:
            # Rate limit exceeded - ждем и пытаемся снова
            logger.warning(f"Rate limit hit, waiting {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            return await self._send_to_user(broadcast, user)

        except Exception as e:
            # Прочие ошибки
            logger.error(f"Error sending to user {user.id}: {e}", exc_info=True)
            self.sent_count += 1
            self.failed_count += 1
            await self.service.add_broadcast_error(
                self.broadcast_id,
                user.id,
                f"Error: {str(e)}",
            )
            return False

    def _build_keyboard(self, buttons_data: dict[str, Any]) -> InlineKeyboardMarkup:
        """Построить inline клавиатуру из данных.

        Args:
            buttons_data: Данные кнопок в формате:
                {
                    "rows": [
                        [{"text": "Button 1", "url": "https://..."}],
                        [{"text": "Button 2", "callback_data": "..."}],
                    ]
                }

        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()

        for row in buttons_data.get("rows", []):
            buttons = []
            for button_data in row:
                button = InlineKeyboardButton(
                    text=button_data["text"],
                    url=button_data.get("url"),
                    callback_data=button_data.get("callback_data"),
                )
                buttons.append(button)
            builder.row(*buttons)

        return builder.as_markup()

    def cancel(self) -> None:
        """Отменить рассылку."""
        self.cancelled = True
        logger.info(f"Broadcast {self.broadcast_id} cancellation requested")
