"""Обработчики чата с поддержкой/администратором."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.database.models.user import User, UserRole

logger = get_logger(__name__)

router = Router(name="support_chat")


class SupportChatStates(StatesGroup):
    """Состояния чата с поддержкой."""

    WAITING_MESSAGE = State()


@router.callback_query(F.data == "support:start")
async def start_support_chat(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Начать чат с администратором.

    Args:
        callback: CallbackQuery
        state: FSM контекст
        user: Пользователь
    """
    text = (
        "💬 <b>Чат с администратором</b>\n\n"
        "Напишите ваше сообщение, и мы ответим вам в ближайшее время.\n\n"
        "💡 <i>Вы можете задать вопрос о товарах, заказе или любой другой теме.</i>\n\n"
        "Для отмены нажмите кнопку ниже."
    )

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text="❌ Отменить", callback_data="support:cancel")
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML",
    )

    await state.set_state(SupportChatStates.WAITING_MESSAGE)
    await callback.answer()

    logger.info(
        "Support chat started",
        user_id=user.id,
    )


@router.callback_query(F.data == "support:cancel")
async def cancel_support_chat(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Отменить чат с администратором.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await state.clear()

    from src.bot.keyboards.main_menu import get_user_menu

    text = "❌ Отменено\n\nВы можете начать новый чат в любое время."

    await callback.message.edit_text(
        text=text,
        reply_markup=get_user_menu(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SupportChatStates.WAITING_MESSAGE)
async def process_support_message(
    message: Message,
    state: FSMContext,
    user: User,
) -> None:
    """Обработать сообщение в чат поддержки.

    Args:
        message: Message от пользователя
        state: FSM контекст
        user: Пользователь
    """
    # Пересылаем сообщение всем админам
    if not settings.superadmin_ids:
        await message.answer(
            "❌ К сожалению, служба поддержки временно недоступна. "
            "Попробуйте позже."
        )
        await state.clear()
        return

    notification_text = (
        f"💬 <b>Новое сообщение от пользователя</b>\n\n"
        f"👤 {user.full_name}"
    )
    if user.username:
        notification_text += f" (@{user.username})"

    notification_text += f"\nID: <code>{user.telegram_id}</code>\n\n"

    # Добавляем текст сообщения
    if message.text:
        notification_text += f"<b>Сообщение:</b>\n{message.text}\n\n"
    elif message.caption:
        notification_text += f"<b>Сообщение:</b>\n{message.caption}\n\n"

    notification_text += (
        "<i>Для ответа перешлите это сообщение обратно "
        "с вашим ответом (Reply).</i>"
    )

    # Отправляем уведомление всем админам
    success_count = 0
    for admin_id in settings.superadmin_ids:
        try:
            if message.photo:
                # Если есть фото, отправляем фото
                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=message.photo[-1].file_id,
                    caption=notification_text,
                    parse_mode="HTML",
                )
            elif message.video:
                # Если есть видео
                await message.bot.send_video(
                    chat_id=admin_id,
                    video=message.video.file_id,
                    caption=notification_text,
                    parse_mode="HTML",
                )
            elif message.document:
                # Если есть документ
                await message.bot.send_document(
                    chat_id=admin_id,
                    document=message.document.file_id,
                    caption=notification_text,
                    parse_mode="HTML",
                )
            else:
                # Просто текст
                await message.bot.send_message(
                    chat_id=admin_id,
                    text=notification_text,
                    parse_mode="HTML",
                )
            success_count += 1
        except Exception as e:
            logger.error(
                "Failed to notify admin about support message",
                admin_id=admin_id,
                user_id=user.id,
                error=str(e),
            )

    if success_count > 0:
        await message.answer(
            "✅ <b>Сообщение отправлено!</b>\n\n"
            "Администратор получил ваше сообщение и ответит в ближайшее время.\n\n"
            "💡 <i>Вы можете продолжить работу с ботом. "
            "Мы уведомим вас, когда получим ответ.</i>",
            parse_mode="HTML",
        )
        logger.info(
            "Support message sent to admins",
            user_id=user.id,
            admins_notified=success_count,
        )
    else:
        await message.answer(
            "❌ Не удалось отправить сообщение. Попробуйте позже."
        )

    # Очищаем состояние
    await state.clear()


@router.message(F.reply_to_message, F.from_user.id.in_(settings.superadmin_ids or []))
async def handle_admin_reply_to_user(
    message: Message,
    session: AsyncSession,
) -> None:
    """Обработать ответ администратора пользователю.

    Args:
        message: Message от админа (reply)
        session: Сессия БД
    """
    # Проверяем, что это ответ на сообщение от бота
    if not message.reply_to_message or not message.reply_to_message.from_user.is_bot:
        return

    replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""

    # Ищем ID пользователя в тексте
    import re
    user_id_pattern = r"ID:\s*<code>(\d+)</code>"
    match = re.search(user_id_pattern, replied_text)

    if not match:
        # Не нашли ID пользователя - это не наше сообщение
        return

    user_telegram_id = int(match.group(1))

    # Формируем ответ для пользователя
    response_text = (
        f"💬 <b>Ответ от администратора:</b>\n\n"
        f"{message.text or message.caption or '(медиа без текста)'}\n\n"
        f"<i>Если у вас есть дополнительные вопросы, "
        f"используйте кнопку 'Связаться с администратором' в меню.</i>"
    )

    try:
        if message.photo:
            await message.bot.send_photo(
                chat_id=user_telegram_id,
                photo=message.photo[-1].file_id,
                caption=response_text,
                parse_mode="HTML",
            )
        elif message.video:
            await message.bot.send_video(
                chat_id=user_telegram_id,
                video=message.video.file_id,
                caption=response_text,
                parse_mode="HTML",
            )
        elif message.document:
            await message.bot.send_document(
                chat_id=user_telegram_id,
                document=message.document.file_id,
                caption=response_text,
                parse_mode="HTML",
            )
        else:
            await message.bot.send_message(
                chat_id=user_telegram_id,
                text=response_text,
                parse_mode="HTML",
            )

        await message.answer("✅ Ответ отправлен пользователю")
        logger.info(
            "Admin reply sent to user",
            admin_id=message.from_user.id,
            user_telegram_id=user_telegram_id,
        )
    except Exception as e:
        logger.error(
            "Failed to send admin reply to user",
            admin_id=message.from_user.id,
            user_telegram_id=user_telegram_id,
            error=str(e),
        )
        await message.answer("❌ Не удалось отправить ответ пользователю")
