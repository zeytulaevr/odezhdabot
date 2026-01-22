"""Обработчики просмотра заказов пользователя."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.orders import get_my_orders_keyboard, get_order_detail_keyboard
from src.core.logging import get_logger
from src.database.models.user import User
from src.services.order_service import OrderService
from src.services.notification_service import NotificationService
from src.utils.navigation import edit_message_with_navigation

logger = get_logger(__name__)

router = Router(name="my_orders")


def format_order_short(order) -> str:
    """Форматировать краткую информацию о заказе.

    Args:
        order: Заказ

    Returns:
        Отформатированная строка
    """
    status_emoji = NotificationService.get_status_emoji(order.status)
    status_name = NotificationService.get_status_name(order.status)
    product_name = order.product.name if order.product else "Неизвестный товар"

    return (
        f"{status_emoji} <b>Заказ #{order.id}</b>\n"
        f"📦 {product_name}\n"
        f"📏 Размер: {order.size.upper()}\n"
        f"📅 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"Статус: <b>{status_name}</b>"
    )


def format_order_detail(order) -> str:
    """Форматировать детальную информацию о заказе.

    Args:
        order: Заказ

    Returns:
        Отформатированная строка
    """
    status_emoji = NotificationService.get_status_emoji(order.status)
    status_name = NotificationService.get_status_name(order.status)

    product_name = order.product.name if order.product else "Неизвестный товар"
    product_price = order.product.formatted_price if order.product else "—"

    text = (
        f"{status_emoji} <b>Заказ #{order.id}</b>\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Цена: {product_price}\n"
        f"📏 Размер: {order.size.upper()}\n"
        f"📞 Контакт: {order.customer_contact}\n"
        f"📅 Создан: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Статус:</b> {status_name}"
    )

    if order.admin_notes:
        text += f"\n\n💬 <b>Комментарий:</b>\n{order.admin_notes}"

    return text


@router.callback_query(F.data == "my_orders")
@router.callback_query(F.data == "my_orders_refresh")
@router.message(F.text == "🛍 Мои заказы")
async def show_my_orders(
    event: Message | CallbackQuery,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    """Показать список заказов пользователя.

    Args:
        event: Message или CallbackQuery
        session: Сессия БД
        user: Пользователь
        state: FSM контекст
    """
    order_service = OrderService(session)
    orders = await order_service.get_user_orders(user_id=user.id, limit=20)

    if not orders:
        text = (
            "📭 <b>У вас пока нет заказов</b>\n\n"
            "Посмотрите каталог товаров и сделайте первый заказ!"
        )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="📦 Каталог",
                callback_data="catalog",
            )
        )
        keyboard = builder.as_markup()
    else:
        text = f"🛍 <b>Мои заказы</b>\n\nВсего заказов: {len(orders)}\n\n"

        # Список заказов
        for order in orders[:10]:  # Показываем максимум 10
            text += "─────────────────\n"
            text += format_order_short(order) + "\n\n"

        text += (
            "Нажмите на заказ для просмотра деталей.\n"
            "Используйте команду /cancel для отмены заказа."
        )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        # Кнопки заказов (последние 10)
        for order in orders[:10]:
            status_emoji = NotificationService.get_status_emoji(order.status)
            builder.row(
                InlineKeyboardButton(
                    text=f"{status_emoji} Заказ #{order.id}",
                    callback_data=f"order_detail:{order.id}",
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="🔄 Обновить",
                callback_data="my_orders_refresh",
            )
        )

        keyboard = builder.as_markup()

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

    logger.info(
        "My orders viewed",
        user_id=user.id,
        orders_count=len(orders),
    )


@router.callback_query(F.data.startswith("order_detail:"))
async def show_order_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    """Показать детали заказа.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    # Проверяем что заказ принадлежит пользователю
    if order.user_id != user.id:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    text = format_order_detail(order)
    keyboard = get_order_detail_keyboard(order)

    await edit_message_with_navigation(
        callback=callback,
        state=state,
        text=text,
        markup=keyboard,
    )

    logger.info(
        "Order detail viewed",
        user_id=user.id,
        order_id=order_id,
    )


@router.callback_query(F.data.startswith("order_user_cancel:"))
async def cancel_user_order(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    """Отменить заказ (пользователем).

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
        state: FSM контекст
    """
    order_id = int(callback.data.split(":")[1])

    order_service = OrderService(session)
    order = await order_service.get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    # Проверяем что заказ принадлежит пользователю
    if order.user_id != user.id:
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return

    # Проверяем можно ли отменить
    if not order.can_be_cancelled:
        await callback.answer(
            "❌ Этот заказ уже нельзя отменить",
            show_alert=True,
        )
        return

    old_status = order.status

    # Отменяем заказ
    order = await order_service.cancel_order(
        order_id=order_id,
        reason="Отменено пользователем",
    )

    if order:
        await session.commit()

        # Уведомляем пользователя
        await NotificationService.notify_user_status_change(
            callback.bot, order, old_status
        )

        text = (
            f"❌ <b>Заказ #{order_id} отменён</b>\n\n"
            f"Вы всегда можете сделать новый заказ в каталоге."
        )

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="◀️ Мои заказы",
                callback_data="my_orders",
            )
        )
        keyboard = builder.as_markup()

        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

        await callback.answer("✅ Заказ отменён")

        logger.info(
            "Order cancelled by user",
            user_id=user.id,
            order_id=order_id,
        )
    else:
        await callback.answer(
            "❌ Ошибка отмены заказа",
            show_alert=True,
        )
