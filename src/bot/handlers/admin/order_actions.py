"""Действия администратора с заказами."""

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsAdmin
from src.bot.keyboards.orders import (
    get_order_actions_keyboard,
    get_status_change_confirmation_keyboard,
)
from src.core.logging import get_logger
from src.database.models.user import User
from src.services.order_service import OrderService
from src.services.notification_service import NotificationService

logger = get_logger(__name__)

router = Router(name="admin_order_actions")


async def safe_edit_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> None:
    """Безопасное редактирование сообщения с обработкой ошибки 'message is not modified'.

    Args:
        callback: CallbackQuery
        text: Новый текст сообщения
        reply_markup: Клавиатура
        parse_mode: Режим парсинга
    """
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
    except TelegramBadRequest as e:
        # Игнорируем ошибку "message is not modified"
        if "message is not modified" not in str(e).lower():
            raise


class AdminOrderStates(StatesGroup):
    """Состояния для действий админа с заказами."""

    ADD_NOTE = State()
    SEND_MESSAGE_TO_CLIENT = State()
    EDIT_CONTACT = State()


@router.callback_query(F.data.startswith("admin_order_status:"), IsAdmin())
async def change_order_status(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Изменить статус заказа с подтверждением.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_status = parts[2]

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    old_status_name = NotificationService.get_status_name(order.status)
    new_status_name = NotificationService.get_status_name(new_status)

    text = (
        f"⚠️ <b>Изменение статуса заказа #{order_id}</b>\n\n"
        f"Старый статус: {old_status_name}\n"
        f"<b>Новый статус: {new_status_name}</b>\n\n"
        f"Клиент получит уведомление об изменении.\n"
        f"Подтвердите действие:"
    )

    keyboard = get_status_change_confirmation_keyboard(order_id, new_status)

    await safe_edit_message(
        callback=callback,
        text=text,
        reply_markup=keyboard,
    )

    await callback.answer()


@router.callback_query(F.data.startswith("admin_order_confirm_status:"), IsAdmin())
async def confirm_status_change(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Подтвердить изменение статуса заказа.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
        user: Администратор
    """
    parts = callback.data.split(":")
    order_id = int(parts[1])
    new_status = parts[2]

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    old_status = order.status

    # Обновляем статус
    admin_note = f"Статус изменен администратором {user.full_name}"
    order = await order_service.update_order_status(
        order_id=order_id,
        status=new_status,
        admin_notes=admin_note,
    )

    if order:
        await session.commit()

        # Уведомляем клиента
        await NotificationService.notify_user_status_change(
            callback.bot, order, old_status
        )

        text = (
            f"✅ <b>Статус изменён</b>\n\n"
            f"Заказ #{order_id}\n"
            f"Новый статус: {NotificationService.get_status_name(new_status)}\n\n"
            f"Клиент уведомлён."
        )

        # Возвращаемся к просмотру заказа
        from src.bot.handlers.admin.orders import format_admin_order_detail

        detail_text = format_admin_order_detail(order)
        keyboard = get_order_actions_keyboard(order_id, order.status)

        await safe_edit_message(
            callback=callback,
            text=detail_text,
            reply_markup=keyboard,
        )

        await callback.answer("✅ Статус изменён")

        logger.info(
            "Order status changed by admin",
            admin_id=user.id,
            order_id=order_id,
            old_status=old_status,
            new_status=new_status,
        )
    else:
        await callback.answer("❌ Ошибка изменения статуса", show_alert=True)


@router.callback_query(F.data.startswith("admin_order_note:"), IsAdmin())
async def start_add_note(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать добавление заметки к заказу.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    await state.update_data(order_id=order_id)

    text = (
        f"📝 <b>Добавление заметки</b>\n\n"
        f"Заказ #{order_id}\n\n"
        f"Введите текст заметки или /cancel для отмены:"
    )

    await safe_edit_message(
        callback=callback,
        text=text,
    )

    await state.set_state(AdminOrderStates.ADD_NOTE)
    await callback.answer()


@router.message(AdminOrderStates.ADD_NOTE, F.text, IsAdmin())
async def process_add_note(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Обработать добавление заметки.

    Args:
        message: Message с текстом заметки
        session: Сессия БД
        state: FSM контекст
        user: Администратор
    """
    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return

    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await message.answer("❌ Ошибка: ID заказа не найден")
        await state.clear()
        return

    note = message.text.strip()

    if len(note) < 3:
        await message.answer("❌ Заметка слишком короткая")
        return

    order_service = OrderService(session)

    # Добавляем заметку с подписью админа
    full_note = f"[{user.full_name}]: {note}"
    order = await order_service.add_admin_note(order_id, full_note)

    if order:
        await session.commit()

        text = (
            f"✅ <b>Заметка добавлена</b>\n\n"
            f"Заказ #{order_id}\n\n"
            f"💬 {full_note}"
        )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="◀️ К заказу",
                callback_data=f"admin_order_view:{order_id}",
            )
        )
        keyboard = builder.as_markup()

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

        await state.clear()

        logger.info(
            "Admin note added",
            admin_id=user.id,
            order_id=order_id,
        )
    else:
        await message.answer("❌ Ошибка добавления заметки")
        await state.clear()


@router.callback_query(F.data.startswith("admin_order_send_payment:"), IsAdmin())
async def send_payment_details(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Отправить реквизиты оплаты клиенту.

    Args:
        callback: CallbackQuery
        session: Сессия БД
    """
    order_id = int(callback.data.split(":")[1])

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    # Получаем реквизиты оплаты
    from src.database.models.bot_settings import BotSettings

    bot_settings = await BotSettings.get_settings(session)

    if not bot_settings.payment_details:
        await callback.answer(
            "❌ Реквизиты оплаты не настроены. Обратитесь к администратору.",
            show_alert=True,
        )
        return

    # Формируем сообщение с реквизитами
    payment_text = (
        f"💳 <b>Реквизиты для оплаты заказа #{order.id}</b>\n\n"
        f"💰 <b>Сумма к оплате:</b> {float(order.total_price):.2f} ₽\n\n"
        f"📋 <b>Реквизиты:</b>\n{bot_settings.payment_details}\n\n"
    )

    if bot_settings.payment_instructions:
        payment_text += f"ℹ️ <b>Инструкция:</b>\n{bot_settings.payment_instructions}\n\n"

    payment_text += (
        "После оплаты отправьте подтверждение (скриншот чека) в ответ на это сообщение."
    )

    # Отправляем реквизиты клиенту
    try:
        await callback.bot.send_message(
            chat_id=order.user.telegram_id,
            text=payment_text,
            parse_mode="HTML",
        )

        # Добавляем заметку к заказу
        note = "Реквизиты оплаты отправлены клиенту"
        await order_service.add_admin_note(order_id, note)
        await session.commit()

        await callback.answer("✅ Реквизиты отправлены клиенту", show_alert=True)

        logger.info(
            "Payment details sent to client",
            order_id=order_id,
            client_id=order.user.id,
        )
    except Exception as e:
        logger.error(
            "Failed to send payment details",
            order_id=order_id,
            error=str(e),
        )
        await callback.answer(
            "❌ Не удалось отправить реквизиты. Проверьте, что клиент не заблокировал бота.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("admin_order_chat:"), IsAdmin())
async def start_chat_with_client(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать чат с клиентом (отправить сообщение).

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    await state.update_data(order_id=order_id)

    text = (
        f"💬 <b>Написать клиенту</b>\n\n"
        f"Заказ #{order_id}\n\n"
        f"Введите сообщение для клиента или /cancel для отмены:"
    )

    await safe_edit_message(
        callback=callback,
        text=text,
    )

    await state.set_state(AdminOrderStates.SEND_MESSAGE_TO_CLIENT)
    await callback.answer()


@router.message(AdminOrderStates.SEND_MESSAGE_TO_CLIENT, F.text, IsAdmin())
async def process_send_message_to_client(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Обработать отправку сообщения клиенту.

    Args:
        message: Message с текстом сообщения
        session: Сессия БД
        state: FSM контекст
        user: Администратор
    """
    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return

    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await message.answer("❌ Ошибка: ID заказа не найден")
        await state.clear()
        return

    message_text = message.text.strip()

    if len(message_text) < 3:
        await message.answer("❌ Сообщение слишком короткое")
        return

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await message.answer("❌ Заказ не найден")
        await state.clear()
        return

    # Создаем запись сообщения в БД
    from src.database.models.order_message import OrderMessage

    order_message = OrderMessage(
        order_id=order_id,
        sender_id=user.id,
        message_text=message_text,
        is_read=False,
    )

    session.add(order_message)
    await session.flush()

    # Отправляем сообщение клиенту
    try:
        client_text = (
            f"💬 <b>Сообщение по заказу #{order_id}</b>\n\n"
            f"{message_text}\n\n"
            f"<i>Вы можете ответить на это сообщение, и администратор его увидит.</i>"
        )

        await message.bot.send_message(
            chat_id=order.user.telegram_id,
            text=client_text,
            parse_mode="HTML",
        )

        await session.commit()

        text = (
            f"✅ <b>Сообщение отправлено</b>\n\n"
            f"Заказ #{order_id}\n\n"
            f"📤 {message_text}"
        )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="◀️ К заказу",
                callback_data=f"admin_order_view:{order_id}",
            )
        )
        keyboard = builder.as_markup()

        await message.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

        await state.clear()

        logger.info(
            "Message sent to client",
            admin_id=user.id,
            order_id=order_id,
            client_id=order.user.id,
        )
    except Exception as e:
        await session.rollback()
        logger.error(
            "Failed to send message to client",
            order_id=order_id,
            error=str(e),
        )
        await message.answer(
            "❌ Не удалось отправить сообщение. Проверьте, что клиент не заблокировал бота."
        )
        await state.clear()


@router.callback_query(F.data.startswith("admin_order_edit:"), IsAdmin())
async def start_edit_order(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начать редактирование заказа (редактирование контактных данных).

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    await state.update_data(order_id=order_id)

    text = (
        f"✏️ <b>Редактирование заказа #{order_id}</b>\n\n"
        f"<b>Текущий контакт клиента:</b>\n{order.customer_contact}\n\n"
        f"Введите новые контактные данные клиента или /cancel для отмены:"
    )

    await safe_edit_message(
        callback=callback,
        text=text,
    )

    await state.set_state(AdminOrderStates.EDIT_CONTACT)
    await callback.answer()


@router.message(AdminOrderStates.EDIT_CONTACT, F.text, IsAdmin())
async def process_edit_order_contact(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Обработать редактирование контактных данных заказа.

    Args:
        message: Message с новыми контактными данными
        session: Сессия БД
        state: FSM контекст
        user: Администратор
    """
    if message.text == "/cancel":
        await message.answer("❌ Отменено")
        await state.clear()
        return

    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await message.answer("❌ Ошибка: ID заказа не найден")
        await state.clear()
        return

    new_contact = message.text.strip()

    if len(new_contact) < 5:
        await message.answer("❌ Контактные данные слишком короткие")
        return

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await message.answer("❌ Заказ не найден")
        await state.clear()
        return

    old_contact = order.customer_contact
    order.customer_contact = new_contact

    # Добавляем заметку об изменении
    note = f"Контакт изменен администратором {user.full_name}\nСтарый: {old_contact}\nНовый: {new_contact}"
    if order.admin_notes:
        order.admin_notes += f"\n\n{note}"
    else:
        order.admin_notes = note

    await session.flush()
    await session.commit()

    text = (
        f"✅ <b>Контакт обновлен</b>\n\n"
        f"Заказ #{order_id}\n\n"
        f"📞 <b>Новый контакт:</b>\n{new_contact}"
    )

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ К заказу",
            callback_data=f"admin_order_view:{order_id}",
        )
    )
    keyboard = builder.as_markup()

    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.clear()

    logger.info(
        "Order contact updated by admin",
        admin_id=user.id,
        order_id=order_id,
    )
