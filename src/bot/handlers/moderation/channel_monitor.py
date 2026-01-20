"""Мониторинг сообщений в канале и автоматическая модерация."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.moderation import get_moderation_keyboard
from src.core.config import settings
from src.core.logging import get_logger
from src.database.repositories.user import UserRepository
from src.services.moderation_service import ModerationService

logger = get_logger(__name__)

router = Router(name="channel_monitor")


@router.channel_post(F.text)
async def monitor_channel_message(
    message: Message,
    session: AsyncSession,
) -> None:
    """Мониторинг сообщений в канале.

    Args:
        message: Сообщение из канала
        session: Сессия БД
    """
    # Пропускаем сообщения от бота
    if message.from_user and message.from_user.is_bot:
        return

    # Проверяем, что это сообщение из настроенного канала (опционально)
    # if message.chat.id != settings.reviews_channel_id:
    #     return

    logger.info(
        "Channel message received",
        message_id=message.message_id,
        chat_id=message.chat.id,
        thread_id=message.message_thread_id,
        from_user=message.from_user.id if message.from_user else None,
    )

    # Получаем текст сообщения
    text = message.text or message.caption or ""
    if not text:
        logger.debug("Message has no text, skipping moderation")
        return

    # Получаем или создаём пользователя в БД
    user_id = None
    if message.from_user:
        user_repo = UserRepository(session)
        user, _ = await user_repo.get_or_create(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name or "Unknown",
            username=message.from_user.username,
        )
        user_id = user.id

    # Модерация сообщения
    moderation_service = ModerationService(session)

    try:
        decision = await moderation_service.moderate_message(
            message_id=message.message_id,
            chat_id=message.chat.id,
            user_id=user_id,
            text=text,
            thread_id=message.message_thread_id,
        )

        logger.info(
            "Moderation decision made",
            message_id=message.message_id,
            spam_score=decision.spam_score,
            status=decision.status,
            should_delete=decision.should_delete,
        )

        # Автоматическое удаление при высоком spam score
        if decision.should_delete:
            try:
                await message.delete()
                logger.warning(
                    "Message auto-deleted",
                    message_id=message.message_id,
                    spam_score=decision.spam_score,
                    reasons=decision.reasons,
                )

                # Уведомляем админов об автоматическом удалении
                await notify_admins_auto_delete(
                    message, decision, session
                )

            except Exception as e:
                logger.error(
                    "Failed to delete message",
                    message_id=message.message_id,
                    error=str(e),
                )

        # Отправка на ручную модерацию
        elif decision.should_notify_admins:
            await notify_admins_for_review(
                message, decision, session
            )

    except Exception as e:
        logger.error(
            "Moderation failed",
            message_id=message.message_id,
            error=str(e),
            exc_info=True,
        )


async def notify_admins_auto_delete(
    message: Message,
    decision,
    session: AsyncSession,
) -> None:
    """Уведомить админов об автоматическом удалении.

    Args:
        message: Удалённое сообщение
        decision: Решение модерации
        session: Сессия БД
    """
    from aiogram import Bot

    # Получаем репозиторий для поиска записи модерации
    from src.database.repositories.moderated_message import ModeratedMessageRepository

    mod_repo = ModeratedMessageRepository(session)
    moderated_msg = await mod_repo.get_by_message_id(
        message.message_id, message.chat.id
    )

    if not moderated_msg:
        logger.error("Moderated message not found for notification")
        return

    # Формируем уведомление
    user_info = (
        f"@{message.from_user.username}" if message.from_user and message.from_user.username
        else f"ID: {message.from_user.id}" if message.from_user
        else "Unknown"
    )

    text = (
        f"🚨 <b>Автоматически удалено</b>\n\n"
        f"👤 Пользователь: {user_info}\n"
        f"📊 Спам-скор: <code>{decision.spam_score}/100</code>\n\n"
        f"📝 <b>Текст сообщения:</b>\n"
        f"<code>{message.text[:500]}</code>\n\n"
        f"⚠️ <b>Причины:</b>\n"
    )

    for reason in decision.reasons[:5]:  # Показываем первые 5 причин
        text += f"• {reason}\n"

    # Отправляем админам
    bot = message.bot
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


async def notify_admins_for_review(
    message: Message,
    decision,
    session: AsyncSession,
) -> None:
    """Отправить сообщение админам на ручную проверку.

    Args:
        message: Сообщение для проверки
        decision: Решение модерации
        session: Сессия БД
    """
    from aiogram import Bot

    # Получаем запись модерации
    from src.database.repositories.moderated_message import ModeratedMessageRepository

    mod_repo = ModeratedMessageRepository(session)
    moderated_msg = await mod_repo.get_by_message_id(
        message.message_id, message.chat.id
    )

    if not moderated_msg:
        logger.error("Moderated message not found for notification")
        return

    # Формируем уведомление
    user_info = (
        f"@{message.from_user.username}" if message.from_user and message.from_user.username
        else f"ID: {message.from_user.id}" if message.from_user
        else "Unknown"
    )

    text = (
        f"⚠️ <b>Требуется проверка</b>\n\n"
        f"👤 Пользователь: {user_info}\n"
        f"📊 Спам-скор: <code>{decision.spam_score}/100</code>\n\n"
        f"📝 <b>Текст сообщения:</b>\n"
        f"<code>{message.text[:500]}</code>\n\n"
    )

    if decision.reasons:
        text += f"⚠️ <b>Подозрения:</b>\n"
        for reason in decision.reasons[:5]:
            text += f"• {reason}\n"

    # Клавиатура с действиями
    keyboard = get_moderation_keyboard(moderated_msg.id)

    # Отправляем админам
    bot = message.bot
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
