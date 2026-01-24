"""FSM диалог оформления заказа."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.orders import (
    get_color_selection_keyboard,
    get_size_selection_keyboard,
    get_quantity_selection_keyboard,
    get_contact_request_keyboard,
    get_order_confirmation_keyboard,
    get_order_completed_keyboard,
)
from src.core.logging import get_logger
from src.database.models.user import User
from src.services.order_service import OrderService
from src.services.product_service import ProductService
from src.services.notification_service import NotificationService
from src.utils.navigation import NavigationStack

logger = get_logger(__name__)

router = Router(name="order_dialog")


class OrderStates(StatesGroup):
    """Состояния оформления заказа."""

    SELECT_COLOR = State()
    SELECT_SIZE = State()
    SELECT_QUANTITY = State()
    ENTER_CONTACT = State()
    CONFIRM = State()


@router.callback_query(F.data.startswith("order_start:"))
async def start_order(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начать оформление заказа - выбор размера."""
    
    product_id = int(callback.data.split(":")[1])
    product_service = ProductService(session)
    product = await product_service.get_product(product_id)

    if not product or not product.is_active:
        await callback.answer("❌ Товар недоступен", show_alert=True)
        return

    if not product.sizes_list:
        await callback.answer("❌ Нет доступных размеров", show_alert=True)
        return

    # Сохраняем данные в state
    await state.update_data(
        product_id=product.id,
        product_name=product.name,
        product_price=product.formatted_price,
        product_fit=product.fit,
    )

    # Проверяем наличие цветов
    if product.colors_list:
        # Если есть цвета - сначала выбираем цвет
        text = (
            f"🛒 <b>Оформление заказа</b>\n\n"
            f"📦 Товар: {product.name}\n"
            f"💰 Цена: {product.formatted_price}\n\n"
            f"Выберите цвет:"
        )

        keyboard = get_color_selection_keyboard(
            product_id=product.id,
            colors=product.colors_list,
        )

        await state.set_state(OrderStates.SELECT_COLOR)
    else:
        # Если цветов нет - сразу выбираем размер
        text = (
            f"🛒 <b>Оформление заказа</b>\n\n"
            f"📦 Товар: {product.name}\n"
            f"💰 Цена: {product.formatted_price}\n\n"
        )

        # Добавляем информацию о крое если есть
        if product.fit:
            text += f"👔 Крой: {product.fit}\n\n"

        text += "Выберите размер:"

        keyboard = get_size_selection_keyboard(
            product_id=product.id,
            sizes=product.sizes_list,
            fit=product.fit,
        )

        await state.set_state(OrderStates.SELECT_SIZE)

    async def safe_edit_or_send():
        """Пытаемся редактировать сообщение, если не получится — отправляем новое"""
        # Если сообщение с фото, удаляем и отправляем новое
        if callback.message.photo:
            await callback.message.delete()
            await callback.message.answer(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            try:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            except TelegramBadRequest:
                # fallback: новое сообщение
                await callback.message.answer(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )

    await safe_edit_or_send()
    await callback.answer()

    logger.info(
        "Order started",
        user_id=callback.from_user.id,
        product_id=product.id,
        has_colors=len(product.colors_list) > 0,
    )


@router.callback_query(OrderStates.SELECT_COLOR, F.data.startswith("order_color:"))
async def process_color_selection(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка выбора цвета - переход к выбору размера.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    parts = callback.data.split(":")
    product_id = int(parts[1])
    color = parts[2]

    # Получаем товар для отображения размеров
    product_service = ProductService(session)
    product = await product_service.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Сохраняем цвет
    await state.update_data(color=color)

    data = await state.get_data()
    product_name = data.get("product_name", "Товар")
    product_price = data.get("product_price", "—")
    product_fit = data.get("product_fit")

    text = (
        f"🛒 <b>Оформление заказа</b>\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Цена: {product_price}\n"
        f"🎨 Цвет: {color}\n\n"
    )

    # Добавляем информацию о крое если есть
    if product_fit:
        text += f"👔 Крой: {product_fit}\n\n"

    text += "Выберите размер:"

    keyboard = get_size_selection_keyboard(
        product_id=product.id,
        sizes=product.sizes_list,
        fit=product_fit,
        color=color,
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(OrderStates.SELECT_SIZE)
    await callback.answer()

    logger.info(
        "Color selected",
        user_id=callback.from_user.id,
        product_id=product_id,
        color=color,
    )


@router.callback_query(OrderStates.SELECT_SIZE, F.data.startswith("order_size:"))
async def process_size_selection(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обработка выбора размера - запрос контакта.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    parts = callback.data.split(":")
    product_id = int(parts[1])
    size = parts[2]
    # Цвет может быть передан как 4-й параметр (если был выбран)
    color_from_callback = parts[3] if len(parts) > 3 else None

    # Обновляем данные
    await state.update_data(size=size)

    # Сохраняем цвет если он был передан
    if color_from_callback:
        await state.update_data(color=color_from_callback)

    data = await state.get_data()
    product_name = data.get("product_name", "Товар")
    product_price = data.get("product_price", "—")
    color = data.get("color") or color_from_callback

    text = (
        f"🛒 <b>Оформление заказа</b>\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Цена: {product_price}\n"
    )

    if color:
        text += f"🎨 Цвет: {color}\n"

    text += (
        f"📏 Размер: {size.upper()}\n\n"
        f"Выберите количество:"
    )

    keyboard = get_quantity_selection_keyboard(product_id, size, color)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(OrderStates.SELECT_QUANTITY)
    await callback.answer()

    logger.info(
        "Size selected",
        user_id=callback.from_user.id,
        product_id=product_id,
        size=size,
        color=color,
    )


@router.callback_query(OrderStates.SELECT_QUANTITY, F.data.startswith("order_quantity:"))
async def process_quantity_selection(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Обработка выбора количества - запрос контакта.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    parts = callback.data.split(":")
    product_id = int(parts[1])
    size = parts[2]
    quantity = int(parts[3])
    # Цвет может быть передан как 5-й параметр
    color_from_callback = parts[4] if len(parts) > 4 else None

    # Обновляем данные
    await state.update_data(quantity=quantity)

    # Сохраняем цвет если он был передан
    if color_from_callback:
        await state.update_data(color=color_from_callback)

    data = await state.get_data()
    product_name = data.get("product_name", "Товар")
    product_price = data.get("product_price", "—")
    color = data.get("color") or color_from_callback

    text = (
        f"🛒 <b>Оформление заказа</b>\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Цена: {product_price}\n"
    )

    if color:
        text += f"🎨 Цвет: {color}\n"

    text += (
        f"📏 Размер: {size.upper()}\n"
        f"🔢 Количество: {quantity} шт.\n\n"
        f"Теперь поделитесь вашим контактом для связи:\n"
        f"• Нажмите кнопку ниже чтобы поделиться номером телефона\n"
        f"• Или введите контакт вручную (телефон, username, email)"
    )

    keyboard = get_contact_request_keyboard()

    await callback.message.delete()
    await callback.message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(OrderStates.ENTER_CONTACT)
    await callback.answer()

    logger.info(
        "Quantity selected",
        user_id=callback.from_user.id,
        product_id=product_id,
        size=size,
        quantity=quantity,
        color=color,
    )


@router.message(OrderStates.ENTER_CONTACT, F.contact)
async def process_contact_shared(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка переданного контакта через RequestContact.

    Args:
        message: Message с контактом
        state: FSM контекст
    """
    contact = message.contact
    phone = contact.phone_number

    # Сохраняем контакт
    await state.update_data(customer_contact=phone)

    # Переходим к подтверждению
    await show_order_confirmation(message, state)


@router.message(OrderStates.ENTER_CONTACT, F.text == "✏️ Ввести вручную")
async def request_manual_contact(
    message: Message,
    state: FSMContext,
) -> None:
    """Запросить ввод контакта вручную.

    Args:
        message: Message
        state: FSM контекст
    """
    text = (
        "✏️ <b>Ввод контакта</b>\n\n"
        "Введите ваш контакт для связи:\n"
        "• Телефон: +79001234567\n"
        "• Username: @username\n"
        "• Email: email@example.com\n\n"
        "Или нажмите /cancel для отмены"
    )

    await message.answer(
        text=text,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )


@router.message(OrderStates.ENTER_CONTACT, F.text == "❌ Отменить")
@router.message(OrderStates.SELECT_SIZE, Command("cancel"))
@router.message(OrderStates.ENTER_CONTACT, Command("cancel"))
@router.message(OrderStates.CONFIRM, Command("cancel"))
async def cancel_order_dialog(
    message: Message,
    state: FSMContext,
) -> None:
    """Отменить оформление заказа.

    Args:
        message: Message
        state: FSM контекст
    """
    await state.clear()

    text = (
        "❌ <b>Оформление заказа отменено</b>\n\n"
        "Вы можете продолжить просмотр каталога."
    )

    await message.answer(
        text=text,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

    logger.info("Order cancelled", user_id=message.from_user.id)


@router.message(OrderStates.ENTER_CONTACT, F.text)
async def process_manual_contact(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка контакта введенного вручную.

    Args:
        message: Message с контактом
        state: FSM контекст
    """
    contact = message.text.strip()

    if len(contact) < 5:
        await message.answer(
            "❌ Контакт слишком короткий. Введите корректный контакт.",
            parse_mode="HTML",
        )
        return

    # Сохраняем контакт
    await state.update_data(customer_contact=contact)

    # Переходим к подтверждению
    await show_order_confirmation(message, state)


async def show_order_confirmation(
    message: Message,
    state: FSMContext,
) -> None:
    """Показать экран подтверждения заказа.

    Args:
        message: Message
        state: FSM контекст
    """
    data = await state.get_data()

    product_name = data.get("product_name", "Товар")
    product_price = data.get("product_price", "—")
    product_id = data.get("product_id")
    size = data.get("size", "—")
    color = data.get("color")
    quantity = data.get("quantity", 1)
    contact = data.get("customer_contact", "—")

    text = (
        f"✅ <b>Подтверждение заказа</b>\n\n"
        f"Проверьте данные заказа:\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Цена: {product_price}\n"
    )

    if color:
        text += f"🎨 Цвет: {color}\n"

    text += (
        f"📏 Размер: {size.upper()}\n"
        f"🔢 Количество: {quantity} шт.\n"
        f"📞 Контакт: {contact}\n\n"
        f"Все верно?"
    )

    keyboard = get_order_confirmation_keyboard(
        product_id=product_id,
        size=size,
    )

    await message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(OrderStates.CONFIRM)


@router.callback_query(OrderStates.CONFIRM, F.data.startswith("order_confirm:"))
async def confirm_and_create_order(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Подтвердить и создать заказ.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
        user: Пользователь
    """
    data = await state.get_data()

    product_id = data.get("product_id")
    size = data.get("size")
    color = data.get("color")
    quantity = data.get("quantity", 1)
    contact = data.get("customer_contact")

    if not all([product_id, size, contact]):
        await callback.answer("❌ Ошибка данных заказа", show_alert=True)
        await state.clear()
        return

    # Создаем заказ
    order_service = OrderService(session)

    try:
        order = await order_service.create_order(
            user_id=user.id,
            product_id=product_id,
            size=size,
            customer_contact=contact,
            color=color,
            quantity=quantity,
        )

        await session.commit()

        # Уведомляем пользователя
        await NotificationService.notify_user_order_created(callback.bot, order)

        # Уведомляем админов
        await NotificationService.notify_admins_new_order(callback.bot, order)

        text = (
            f"✅ <b>Заказ оформлен!</b>\n\n"
            f"📋 Номер заказа: <code>#{order.id}</code>\n\n"
            f"Мы свяжемся с вами в ближайшее время.\n"
            f"Следите за статусом в разделе 'Мои заказы'."
        )

        await callback.message.edit_text(
            text=text,
            reply_markup=get_order_completed_keyboard(),
            parse_mode="HTML",
        )

        await state.clear()
        await callback.answer("✅ Заказ создан!")

        logger.info(
            "Order created",
            user_id=user.id,
            order_id=order.id,
            product_id=product_id,
        )

    except Exception as e:
        logger.error(
            "Failed to create order",
            user_id=user.id,
            error=str(e),
        )
        await callback.answer(
            "❌ Ошибка создания заказа. Попробуйте позже.",
            show_alert=True,
        )
        await state.clear()


@router.callback_query(OrderStates.CONFIRM, F.data == "order_cancel")
async def cancel_from_confirmation(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Отменить заказ на этапе подтверждения.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await state.clear()

    text = (
        "❌ <b>Заказ отменён</b>\n\n"
        "Вы можете продолжить просмотр каталога."
    )

    # Используем клавиатуру с вариантами действий
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📦 Каталог", callback_data="catalog")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    await callback.answer()
    logger.info("Order cancelled at confirmation", user_id=callback.from_user.id)
