"""FSM диалог создания рассылки."""

import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.broadcast import (
    get_broadcast_cancel_keyboard,
    get_broadcast_filters_keyboard,
    get_broadcast_media_skip_keyboard,
    get_broadcast_preview_keyboard,
)
from src.core.logging import get_logger
from src.database.models.user import User
from src.services.broadcast_service import BroadcastService
from src.utils.broadcast_sender import BroadcastSender

logger = get_logger(__name__)

router = Router(name="broadcast_create")


class BroadcastStates(StatesGroup):
    """Состояния для создания рассылки."""

    TEXT = State()
    MEDIA = State()
    FILTERS = State()
    PREVIEW = State()
    SENDING = State()


@router.callback_query(F.data == "broadcast_create", IsSuperAdmin())
async def start_broadcast_creation(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать создание рассылки.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await state.clear()

    text = (
        "✉️ <b>Создание рассылки</b>\n\n"
        "Шаг 1/4: Введите текст сообщения\n\n"
        "Поддерживается HTML разметка:\n"
        "• <b>жирный</b>\n"
        "• <i>курсив</i>\n"
        "• <code>моноширинный</code>\n"
        "• <a href='url'>ссылка</a>\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
    )

    await state.set_state(BroadcastStates.TEXT)
    await callback.answer()


@router.message(BroadcastStates.TEXT, F.text, IsSuperAdmin())
async def process_broadcast_text(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработать текст рассылки.

    Args:
        message: Message с текстом
        state: FSM контекст
    """
    if message.text == "/cancel":
        await message.answer("❌ Создание рассылки отменено")
        await state.clear()
        return

    if len(message.text) < 10:
        await message.answer("❌ Текст слишком короткий (минимум 10 символов)")
        return

    if len(message.text) > 4096:
        await message.answer("❌ Текст слишком длинный (максимум 4096 символов)")
        return

    # Сохраняем текст
    await state.update_data(text=message.text)

    text = (
        "✉️ <b>Создание рассылки</b>\n\n"
        "Шаг 2/4: Добавьте медиа (опционально)\n\n"
        "Отправьте:\n"
        "• Фото\n"
        "• Видео\n"
        "• Документ\n\n"
        "Или нажмите 'Пропустить' для текстовой рассылки"
    )

    keyboard = get_broadcast_media_skip_keyboard()

    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(BroadcastStates.MEDIA)


@router.callback_query(F.data == "broadcast_media_skip", IsSuperAdmin())
async def skip_broadcast_media(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Пропустить добавление медиа.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await show_filters_step(callback, state)


@router.message(BroadcastStates.MEDIA, F.photo, IsSuperAdmin())
async def process_broadcast_photo(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработать фото для рассылки.

    Args:
        message: Message с фото
        state: FSM контекст
    """
    # Берем самое большое фото
    photo = message.photo[-1]

    await state.update_data(
        media_type="photo",
        media_file_id=photo.file_id,
    )

    await message.answer("✅ Фото добавлено")
    await show_filters_step_message(message, state)


@router.message(BroadcastStates.MEDIA, F.video, IsSuperAdmin())
async def process_broadcast_video(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработать видео для рассылки.

    Args:
        message: Message с видео
        state: FSM контекст
    """
    await state.update_data(
        media_type="video",
        media_file_id=message.video.file_id,
    )

    await message.answer("✅ Видео добавлено")
    await show_filters_step_message(message, state)


@router.message(BroadcastStates.MEDIA, F.document, IsSuperAdmin())
async def process_broadcast_document(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработать документ для рассылки.

    Args:
        message: Message с документом
        state: FSM контекст
    """
    await state.update_data(
        media_type="document",
        media_file_id=message.document.file_id,
    )

    await message.answer("✅ Документ добавлен")
    await show_filters_step_message(message, state)


async def show_filters_step(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Показать шаг выбора фильтров.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    data = await state.get_data()
    filters = data.get("filters", {})

    text = (
        "✉️ <b>Создание рассылки</b>\n\n"
        "Шаг 3/4: Выберите получателей\n\n"
        "Выберите один или несколько фильтров:\n"
        "• Все пользователи - без фильтрации\n"
        "• Активные - писали боту последние 30 дней\n"
        "• Есть заказы - сделали хотя бы 1 заказ\n"
        "• Нет заказов - еще не заказывали\n"
        "• Минимум 3 заказа - постоянные клиенты\n\n"
        "Нажмите 'Продолжить' после выбора"
    )

    keyboard = get_broadcast_filters_keyboard(filters)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(BroadcastStates.FILTERS)
    await callback.answer()


async def show_filters_step_message(
    message: Message,
    state: FSMContext,
) -> None:
    """Показать шаг выбора фильтров (для Message).

    Args:
        message: Message
        state: FSM контекст
    """
    data = await state.get_data()
    filters = data.get("filters", {})

    text = (
        "✉️ <b>Создание рассылки</b>\n\n"
        "Шаг 3/4: Выберите получателей\n\n"
        "Выберите один или несколько фильтров:\n"
        "• Все пользователи - без фильтрации\n"
        "• Активные - писали боту последние 30 дней\n"
        "• Есть заказы - сделали хотя бы 1 заказ\n"
        "• Нет заказов - еще не заказывали\n"
        "• Минимум 3 заказа - постоянные клиенты\n\n"
        "Нажмите 'Продолжить' после выбора"
    )

    keyboard = get_broadcast_filters_keyboard(filters)

    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(BroadcastStates.FILTERS)


@router.callback_query(F.data.startswith("broadcast_filter_toggle:"), IsSuperAdmin())
async def toggle_broadcast_filter(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Переключить фильтр.

    Args:
        callback: CallbackQuery
        state: FSM контекст
        session: Сессия БД
    """
    filter_key = callback.data.split(":")[1]

    data = await state.get_data()
    filters = data.get("filters", {})

    # Обработка переключения фильтров
    if filter_key == "all":
        # Если выбрано "все", сбрасываем остальные фильтры
        filters = {"all": not filters.get("all", False)}
    else:
        # Убираем "все" если был выбран
        filters.pop("all", None)

        if filter_key == "active_30":
            if "active_days" in filters:
                del filters["active_days"]
            else:
                filters["active_days"] = 30

        elif filter_key == "has_orders":
            if filters.get("has_orders"):
                del filters["has_orders"]
            else:
                filters["has_orders"] = True
                filters.pop("no_orders", None)  # Взаимоисключающие

        elif filter_key == "no_orders":
            if filters.get("no_orders"):
                del filters["no_orders"]
            else:
                filters["no_orders"] = True
                filters.pop("has_orders", None)  # Взаимоисключающие

        elif filter_key == "min_orders_3":
            if "min_orders" in filters:
                del filters["min_orders"]
            else:
                filters["min_orders"] = 3

    await state.update_data(filters=filters)

    # Получаем количество получателей
    service = BroadcastService(session)
    target_users = await service.get_target_users(filters)
    target_count = len(target_users)

    # Обновляем клавиатуру
    keyboard = get_broadcast_filters_keyboard(filters)

    text = (
        "✉️ <b>Создание рассылки</b>\n\n"
        "Шаг 3/4: Выберите получателей\n\n"
        "Выберите один или несколько фильтров:\n"
        "• Все пользователи - без фильтрации\n"
        "• Активные - писали боту последние 30 дней\n"
        "• Есть заказы - сделали хотя бы 1 заказ\n"
        "• Нет заказов - еще не заказывали\n"
        "• Минимум 3 заказа - постоянные клиенты\n\n"
        f"<b>Получателей по фильтрам: {target_count}</b>"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(F.data == "broadcast_filter_reset", IsSuperAdmin())
async def reset_broadcast_filters(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Сбросить фильтры.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await state.update_data(filters={})
    await show_filters_step(callback, state)


@router.callback_query(F.data == "broadcast_filter_done", IsSuperAdmin())
async def finish_broadcast_filters(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Завершить выбор фильтров и показать предпросмотр.

    Args:
        callback: CallbackQuery
        state: FSM контекст
        session: Сессия БД
    """
    data = await state.get_data()
    filters = data.get("filters", {})

    if not filters:
        await callback.answer("❌ Выберите хотя бы один фильтр", show_alert=True)
        return

    # Получаем количество получателей
    service = BroadcastService(session)
    target_users = await service.get_target_users(filters)
    target_count = len(target_users)

    if target_count == 0:
        await callback.answer("❌ По выбранным фильтрам нет получателей", show_alert=True)
        return

    # Показываем предпросмотр
    text = data.get("text", "")
    media_type = data.get("media_type")

    preview_text = (
        "✉️ <b>Предпросмотр рассылки</b>\n\n"
        f"<b>Получателей:</b> {target_count}\n"
        f"<b>Тип:</b> {'Текст + ' + media_type if media_type else 'Только текст'}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Проверьте сообщение и нажмите 'Отправить'"
    )

    keyboard = get_broadcast_preview_keyboard()

    await callback.message.edit_text(
        text=preview_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(BroadcastStates.PREVIEW)
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_confirm_send"), IsSuperAdmin())
async def confirm_broadcast_send(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Подтвердить и отправить рассылку.

    Args:
        callback: CallbackQuery
        state: FSM контекст
        session: Сессия БД
        user: Администратор
    """
    data = await state.get_data()

    text = data.get("text")
    media_type = data.get("media_type")
    media_file_id = data.get("media_file_id")
    filters = data.get("filters", {})

    if not text:
        await callback.answer("❌ Ошибка: текст не найден", show_alert=True)
        await state.clear()
        return

    # Создаем рассылку в БД
    service = BroadcastService(session)
    broadcast = await service.create_broadcast(
        text=text,
        admin_id=user.id,
        filters=filters,
        media_type=media_type,
        media_file_id=media_file_id,
    )

    await session.commit()

    await callback.message.edit_text(
        text=f"⏳ Рассылка #{broadcast.id} создана\n\nНачинаем отправку...",
        parse_mode="HTML",
    )

    await state.clear()
    await callback.answer()

    # Запускаем отправку в фоне
    asyncio.create_task(
        start_broadcast_sending(
            broadcast_id=broadcast.id,
            bot=callback.bot,
            session=session,
            admin_telegram_id=user.telegram_id,
        )
    )


async def start_broadcast_sending(
    broadcast_id: int,
    bot,
    session: AsyncSession,
    admin_telegram_id: int,
) -> None:
    """Запустить отправку рассылки в фоне.

    Args:
        broadcast_id: ID рассылки
        bot: Бот
        session: Сессия БД
        admin_telegram_id: Telegram ID админа
    """
    try:
        sender = BroadcastSender(bot, session, broadcast_id)
        await sender.send_broadcast(admin_telegram_id=admin_telegram_id)
    except Exception as e:
        logger.error(f"Error during broadcast sending: {e}", exc_info=True)

        # Уведомляем админа об ошибке
        try:
            await bot.send_message(
                chat_id=admin_telegram_id,
                text=f"❌ <b>Ошибка при отправке рассылки #{broadcast_id}</b>\n\n"
                f"Причина: {str(e)}",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data == "broadcast_cancel", IsSuperAdmin())
async def cancel_broadcast_creation(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Отменить создание рассылки.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await state.clear()
    await callback.message.edit_text(
        text="❌ Создание рассылки отменено",
        parse_mode="HTML",
    )
    await callback.answer()
