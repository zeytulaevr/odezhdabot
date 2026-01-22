"""Действия администратора с заказами."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
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


class AdminOrderStates(StatesGroup):
    """Состояния для действий админа с заказами."""

    ADD_NOTE = State()


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

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
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

        await callback.message.edit_text(
            text=detail_text,
            reply_markup=keyboard,
            parse_mode="HTML",
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

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
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
