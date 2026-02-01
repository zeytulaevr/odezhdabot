"""Обработчики управления заказами для админов."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsAdmin
from src.bot.keyboards.orders import (
    get_admin_orders_filters_keyboard,
    get_order_actions_keyboard,
)
from src.core.logging import get_logger
from src.database.models.user import User
from src.services.order_service import OrderService
from src.services.notification_service import NotificationService
from src.utils.navigation import edit_message_with_navigation

logger = get_logger(__name__)

router = Router(name="admin_orders")


def format_admin_order_list(orders: list, status_filter: str = "all") -> str:
    """Форматировать список заказов для админа.

    Args:
        orders: Список заказов
        status_filter: Текущий фильтр

    Returns:
        Отформатированная строка
    """
    if not orders:
        return (
            f"📋 <b>Заказы ({status_filter})</b>\n\n"
            "Нет заказов с таким статусом."
        )

    text = f"📋 <b>Заказы ({status_filter})</b>\n\n"
    text += f"Найдено: {len(orders)}\n\n"

    for order in orders[:15]:  # Показываем максимум 15
        status_emoji = NotificationService.get_status_emoji(order.status)

        # Формируем описание товаров
        if order.items:
            items_count = order.total_items
            items_desc = f"{items_count} товар(ов)"
        else:
            items_desc = "Нет товаров"

        text += (
            f"{status_emoji} <b>#{order.id}</b> - {items_desc}\n"
            f"👤 {order.user.full_name}\n"
            f"📞 {order.customer_contact}\n"
            f"💰 {float(order.total_price):.2f} ₽\n"
            f"📅 {order.created_at.strftime('%d.%m %H:%M')}\n"
            "─────────────\n"
        )

    text += "\nНажмите на заказ для управления."

    return text


def format_admin_order_detail(order) -> str:
    """Форматировать детали заказа для админа.

    Args:
        order: Заказ

    Returns:
        Отформатированная строка
    """
    status_emoji = NotificationService.get_status_emoji(order.status)
    status_name = NotificationService.get_status_name(order.status)

    text = (
        f"{status_emoji} <b>Заказ #{order.id}</b>\n\n"
        f"━━━━━━━━━━\n"
        f"👤 <b>Клиент:</b> {order.user.full_name}\n"
    )

    if order.user.username:
        text += f"📱 <b>Telegram:</b> @{order.user.username}\n"

    text += (
        f"📞 <b>Контакт:</b> {order.customer_contact}\n"
        f"🆔 <b>Telegram ID:</b> <code>{order.user.telegram_id}</code>\n"
        f"🕐 <b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"━━━━━━━━━━\n\n"
    )

    # Список товаров
    if order.items:
        text += f"🛍️ <b>Товары ({order.total_items} шт.):</b>\n\n"
        for i, item in enumerate(order.items, 1):
            text += (
                f"{i}. {item.product_name}\n"
                f"   📏 Размер: {item.size.upper()}"
            )
            if item.color:
                text += f" | 🎨 {item.color}"
            text += (
                f"\n   🔢 {item.quantity} шт. × {float(item.price_at_order):.2f} ₽ = "
                f"{float(item.total_price):.2f} ₽\n\n"
            )
    else:
        text += "📭 <b>Нет товаров в заказе</b>\n\n"

    text += (
        f"━━━━━━━━━━\n"
        f"💰 <b>ИТОГО: {float(order.total_price):.2f} ₽</b>\n"
        f"━━━━━━━━━━\n\n"
        f"<b>Статус:</b> {status_name}\n"
        f"<b>Обновлён:</b> {order.updated_at.strftime('%d.%m.%Y %H:%M')}"
    )

    if order.admin_notes:
        text += f"\n\n💬 <b>Заметки администратора:</b>\n{order.admin_notes}"

    return text


@router.message(Command("admin"), IsAdmin())
@router.callback_query(F.data == "admin_orders", IsAdmin())
async def show_admin_orders(
    event: Message | CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать админ-панель заказов с фильтрами.

    Args:
        event: Message или CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    order_service = OrderService(session)
    stats = await order_service.get_order_stats()

    text = (
        "👨‍💼 <b>Управление заказами</b>\n\n"
        f"🆕 Новые: {stats.get('new', 0)}\n"
        f"⏳ В обработке: {stats.get('processing', 0)}\n"
        f"💰 Оплачены: {stats.get('paid', 0)}\n"
        f"📦 Отправлены: {stats.get('shipped', 0)}\n"
        f"✅ Выполнены: {stats.get('completed', 0)}\n"
        f"❌ Отменены: {stats.get('cancelled', 0)}\n\n"
        f"<b>Всего:</b> {stats.get('total', 0)}\n\n"
        "Выберите фильтр для просмотра заказов:"
    )

    keyboard = get_admin_orders_filters_keyboard(current_filter="all")

    if isinstance(event, CallbackQuery):
        await edit_message_with_navigation(
            callback=event,
            state=state,
            text=text,
            markup=keyboard,
            save_to_history=False,
        )
    else:
        await event.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    logger.info("Admin orders panel opened", user_id=event.from_user.id)


@router.callback_query(F.data.startswith("admin_orders_filter:"), IsAdmin())
async def filter_admin_orders(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Фильтр заказов по статусу.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    status_filter = callback.data.split(":")[1]

    order_service = OrderService(session)

    if status_filter == "all":
        orders = await order_service.get_all_orders(limit=50)
    else:
        orders = await order_service.get_orders_by_status(status_filter, limit=50)

    text = format_admin_order_list(orders, status_filter)

    # Добавляем кнопки заказов
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    for order in orders[:15]:
        status_emoji = NotificationService.get_status_emoji(order.status)
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} Заказ #{order.id}",
                callback_data=f"admin_order_view:{order.id}",
            )
        )

    # Кнопки управления
    builder.row(
        InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data=f"admin_orders_filter:{status_filter}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⚙️ Фильтры",
            callback_data="admin_orders",
        )
    )

    keyboard = builder.as_markup()

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )

    logger.info(
        "Admin orders filtered",
        user_id=callback.from_user.id,
        filter=status_filter,
        count=len(orders),
    )


@router.callback_query(F.data.startswith("admin_order_view:"), IsAdmin())
async def view_admin_order(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Просмотр деталей заказа админом.

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

    text = format_admin_order_detail(order)
    keyboard = get_order_actions_keyboard(order_id, order.status)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )

    logger.info(
        "Admin order viewed",
        user_id=callback.from_user.id,
        order_id=order_id,
    )
