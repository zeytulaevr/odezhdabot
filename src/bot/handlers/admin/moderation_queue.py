"""Обработчики очереди модерации для администраторов."""

import json

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsAdmin
from src.bot.keyboards.moderation import get_moderation_keyboard, get_moderation_queue_keyboard
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.moderated_message import ModeratedMessageRepository
from src.database.repositories.user import UserRepository
from src.services.moderation_service import ModerationService

logger = get_logger(__name__)

router = Router(name="moderation_queue")


@router.message(Command("modqueue"), IsAdmin())
async def cmd_moderation_queue(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Показать очередь модерации.

    Args:
        message: Входящее сообщение
        user: Пользователь (админ)
        session: Сессия БД
    """
    logger.info("Moderation queue requested", admin_id=user.id)

    mod_repo = ModeratedMessageRepository(session)
    pending_messages = await mod_repo.get_pending(limit=10)

    if not pending_messages:
        await message.answer(
            "✅ <b>Очередь модерации пуста</b>\n\n"
            "Нет сообщений, ожидающих проверки.",
            parse_mode="HTML",
        )
        return

    text = f"📋 <b>Очередь модерации</b>\n\n" f"Сообщений на проверке: <b>{len(pending_messages)}</b>\n\n"

    await message.answer(text, parse_mode="HTML")

    # Отправляем каждое сообщение отдельно с кнопками
    for msg in pending_messages:
        user_info = ""
        if msg.user:
            user_info = (
                f"@{msg.user.username}" if msg.user.username else f"ID: {msg.user.telegram_id}"
            )
        else:
            user_info = "Unknown"

        msg_text = (
            f"👤 Пользователь: {user_info}\n"
            f"📊 Спам-скор: <code>{msg.spam_score}/100</code>\n"
            f"📅 Дата: {msg.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"📝 <b>Текст:</b>\n"
            f"<code>{msg.text[:500]}</code>\n"
        )

        if msg.spam_reasons:
            try:
                reasons = json.loads(msg.spam_reasons)
                if reasons:
                    msg_text += f"\n⚠️ <b>Подозрения:</b>\n"
                    for reason in reasons[:3]:
                        msg_text += f"• {reason}\n"
            except json.JSONDecodeError:
                pass

        keyboard = get_moderation_keyboard(msg.id)

        await message.answer(msg_text, reply_markup=keyboard, parse_mode="HTML")

    # Кнопки управления очередью
    has_more = len(pending_messages) >= 10
    await message.answer(
        "Выберите действие:",
        reply_markup=get_moderation_queue_keyboard(has_more),
    )


@router.callback_query(F.data.startswith("mod_approve:"), IsAdmin())
async def callback_approve_message(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Одобрить сообщение.

    Args:
        callback: Callback query
        user: Админ
        session: Сессия БД
    """
    moderated_msg_id = int(callback.data.split(":")[1])

    logger.info(
        "Approving message",
        moderated_msg_id=moderated_msg_id,
        admin_id=user.id,
    )

    moderation_service = ModerationService(session)
    success = await moderation_service.approve_message_by_admin(
        moderated_msg_id, user.id, comment="Одобрено администратором"
    )

    if success:
        await callback.answer("✅ Сообщение одобрено", show_alert=True)
        if callback.message:
            await callback.message.edit_text(
                f"{callback.message.text}\n\n"
                f"✅ <b>Одобрено</b> администратором {user.username or user.full_name}",
                parse_mode="HTML",
            )
    else:
        await callback.answer("❌ Ошибка при одобрении", show_alert=True)


@router.callback_query(F.data.startswith("mod_reject:"), IsAdmin())
async def callback_reject_message(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Отклонить сообщение.

    Args:
        callback: Callback query
        user: Админ
        session: Сессия БД
    """
    moderated_msg_id = int(callback.data.split(":")[1])

    logger.info(
        "Rejecting message",
        moderated_msg_id=moderated_msg_id,
        admin_id=user.id,
    )

    moderation_service = ModerationService(session)

    # Получаем сообщение для удаления
    mod_repo = ModeratedMessageRepository(session)
    moderated_msg = await mod_repo.get(moderated_msg_id)

    if not moderated_msg:
        await callback.answer("❌ Сообщение не найдено", show_alert=True)
        return

    # Отклоняем
    success = await moderation_service.reject_message_by_admin(
        moderated_msg_id,
        user.id,
        comment="Отклонено администратором",
        delete_message=True,
    )

    if success:
        # Пытаемся удалить сообщение из канала
        try:
            await callback.bot.delete_message(
                chat_id=moderated_msg.chat_id,
                message_id=moderated_msg.message_id,
            )
            await callback.answer("✅ Сообщение отклонено и удалено", show_alert=True)
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")
            await callback.answer(
                "✅ Сообщение отклонено (не удалось удалить из канала)",
                show_alert=True,
            )

        if callback.message:
            await callback.message.edit_text(
                f"{callback.message.text}\n\n"
                f"❌ <b>Отклонено</b> администратором {user.username or user.full_name}",
                parse_mode="HTML",
            )
    else:
        await callback.answer("❌ Ошибка при отклонении", show_alert=True)


@router.callback_query(F.data.startswith("mod_ban"), IsAdmin())
async def callback_ban_user(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Забанить пользователя.

    Args:
        callback: Callback query
        user: Админ
        session: Сессия БД
    """
    parts = callback.data.split(":")
    moderated_msg_id = int(parts[1])

    # Получаем сообщение
    mod_repo = ModeratedMessageRepository(session)
    moderated_msg = await mod_repo.get(moderated_msg_id)

    if not moderated_msg or not moderated_msg.user_id:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    # Баним пользователя
    user_repo = UserRepository(session)
    banned_user = await user_repo.ban_user(moderated_msg.user_id)

    if banned_user:
        # Отклоняем сообщение
        moderation_service = ModerationService(session)
        await moderation_service.reject_message_by_admin(
            moderated_msg_id,
            user.id,
            comment=f"Пользователь забанен: {callback.data}",
            delete_message=True,
        )

        # Удаляем сообщение из канала
        try:
            await callback.bot.delete_message(
                chat_id=moderated_msg.chat_id,
                message_id=moderated_msg.message_id,
            )
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")

        await callback.answer("✅ Пользователь забанен", show_alert=True)

        if callback.message:
            await callback.message.edit_text(
                f"{callback.message.text}\n\n"
                f"🚫 <b>Пользователь забанен</b> администратором {user.username or user.full_name}",
                parse_mode="HTML",
            )
    else:
        await callback.answer("❌ Ошибка при бане пользователя", show_alert=True)


@router.callback_query(F.data == "modqueue_refresh", IsAdmin())
async def callback_refresh_queue(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Обновить очередь модерации.

    Args:
        callback: Callback query
        user: Админ
        session: Сессия БД
    """
    await callback.answer("Обновление очереди...")

    # Эмулируем команду /modqueue
    if callback.message:
        await cmd_moderation_queue(callback.message, user, session)


@router.callback_query(F.data == "modqueue_stats", IsAdmin())
async def callback_moderation_stats(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Показать статистику модерации.

    Args:
        callback: Callback query
        user: Админ
        session: Сессия БД
    """
    mod_repo = ModeratedMessageRepository(session)
    stats = await mod_repo.get_spam_statistics(days=7)

    text = (
        f"📊 <b>Статистика модерации за 7 дней</b>\n\n"
        f"📨 Всего сообщений: <b>{stats['total']}</b>\n"
        f"✅ Одобрено: <b>{stats['approved']}</b>\n"
        f"❌ Отклонено: <b>{stats['rejected']}</b>\n"
        f"⏳ На проверке: <b>{stats['pending']}</b>\n"
    )

    await callback.answer()
    await callback.message.answer(text, parse_mode="HTML")
