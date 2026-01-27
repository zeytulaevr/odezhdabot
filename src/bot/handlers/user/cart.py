"""Обработчики корзины покупок."""

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.cart import (
    get_cart_clear_confirm_keyboard,
    get_cart_item_keyboard,
    get_cart_view_keyboard,
)
from src.bot.keyboards.orders import get_contact_request_keyboard, get_order_completed_keyboard
from src.core.logging import get_logger
from src.database.models.user import User
from src.services.cart_service import CartService
from src.services.notification_service import NotificationService
from src.services.order_service import OrderService

logger = get_logger(__name__)

router = Router(name="user_cart")


class CheckoutStates(StatesGroup):
    """Состояния оформления заказа из корзины."""

    ENTER_CONTACT = State()
    CONFIRM = State()


class QuickOrderStates(StatesGroup):
    """Состояния быстрого заказа товара."""

    ENTER_CONTACT = State()
    CONFIRM = State()


@router.callback_query(F.data == "cart_view")
async def show_cart(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    """Показать содержимое корзины.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
    """
    cart_service = CartService(session)
    cart_items = await cart_service.get_cart_items(user.id)

    if not cart_items:
        text = (
            "🛒 <b>Корзина пуста</b>\n\n"
            "Добавьте товары из каталога!"
        )
    else:
        # Формируем список товаров
        total_price = Decimal("0")
        total_items = 0

        text = "🛒 <b>Ваша корзина</b>\n\n"

        for i, item in enumerate(cart_items, 1):
            product = item.product
            item_price = product.price * item.quantity if product else Decimal("0")
            total_price += item_price
            total_items += item.quantity

            text += f"{i}. <b>{item.display_name}</b>\n"
            if product:
                text += f"   💰 {product.formatted_price} × {item.quantity} = {item_price:,.2f} ₽\n"
            text += "\n"

        text += f"━━━━━━━━━━━━━━━━\n"
        text += f"📦 Всего товаров: {total_items} шт.\n"
        text += f"💰 <b>Итого: {total_price:,.2f} ₽</b>"

    keyboard = get_cart_view_keyboard(cart_items)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()

    logger.info(
        "Cart viewed",
        user_id=user.id,
        items_count=len(cart_items),
    )


@router.callback_query(F.data.startswith("cart_item:"))
async def show_cart_item(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    """Показать детали товара в корзине.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
    """
    cart_item_id = int(callback.data.split(":")[1])

    cart_service = CartService(session)
    cart_items = await cart_service.get_cart_items(user.id)

    # Находим нужный товар
    cart_item = next((item for item in cart_items if item.id == cart_item_id), None)

    if not cart_item:
        await callback.answer("❌ Товар не найден в корзине", show_alert=True)
        return

    product = cart_item.product
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Формируем описание
    text = (
        f"📦 <b>{cart_item.display_name}</b>\n\n"
        f"💰 Цена: {product.formatted_price}\n"
        f"🔢 Количество: {cart_item.quantity} шт.\n"
        f"💵 Сумма: {(product.price * cart_item.quantity):,.2f} ₽\n\n"
    )

    if product.description:
        text += f"📝 {product.description}\n\n"

    text += "Выберите действие:"

    keyboard = get_cart_item_keyboard(cart_item.id, cart_item.quantity)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cart_qty:"))
async def update_cart_item_quantity(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    """Изменить количество товара в корзине.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
    """
    parts = callback.data.split(":")
    cart_item_id = int(parts[1])
    action = parts[2]  # "plus" или "minus"

    cart_service = CartService(session)
    cart_items = await cart_service.get_cart_items(user.id)

    # Находим товар
    cart_item = next((item for item in cart_items if item.id == cart_item_id), None)

    if not cart_item:
        await callback.answer("❌ Товар не найден в корзине", show_alert=True)
        return

    # Изменяем количество
    new_quantity = cart_item.quantity
    if action == "plus":
        new_quantity += 1
    elif action == "minus":
        new_quantity -= 1

    # Обновляем количество
    updated_item = await cart_service.update_quantity(user.id, cart_item_id, new_quantity)
    await session.commit()

    if not updated_item:
        # Товар был удален (количество стало 0)
        await callback.answer("🗑 Товар удален из корзины")
        # Возвращаемся к просмотру корзины
        callback.data = "cart_view"
        await show_cart(callback, session, user)
        return

    # Обновляем отображение
    product = updated_item.product

    text = (
        f"📦 <b>{updated_item.display_name}</b>\n\n"
        f"💰 Цена: {product.formatted_price}\n"
        f"🔢 Количество: {updated_item.quantity} шт.\n"
        f"💵 Сумма: {(product.price * updated_item.quantity):,.2f} ₽\n\n"
    )

    if product.description:
        text += f"📝 {product.description}\n\n"

    text += "Выберите действие:"

    keyboard = get_cart_item_keyboard(updated_item.id, updated_item.quantity)

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer(f"✓ Количество: {updated_item.quantity}")


@router.callback_query(F.data.startswith("cart_remove:"))
async def remove_cart_item(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    """Удалить товар из корзины.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
    """
    cart_item_id = int(callback.data.split(":")[1])

    cart_service = CartService(session)
    success = await cart_service.remove_item(user.id, cart_item_id)
    await session.commit()

    if success:
        await callback.answer("✓ Товар удален из корзины")
    else:
        await callback.answer("❌ Товар не найден", show_alert=True)

    # Показываем корзину
    callback.data = "cart_view"
    await show_cart(callback, session, user)


@router.callback_query(F.data == "cart_clear")
async def confirm_clear_cart(
    callback: CallbackQuery,
) -> None:
    """Подтверждение очистки корзины.

    Args:
        callback: CallbackQuery
    """
    text = (
        "⚠️ <b>Очистить корзину?</b>\n\n"
        "Все товары будут удалены из корзины.\n"
        "Это действие нельзя отменить."
    )

    keyboard = get_cart_clear_confirm_keyboard()

    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "cart_clear_confirm")
async def clear_cart(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
) -> None:
    """Очистить корзину.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
    """
    cart_service = CartService(session)
    await cart_service.clear_cart(user.id)
    await session.commit()

    await callback.answer("✓ Корзина очищена")

    # Показываем пустую корзину
    callback.data = "cart_view"
    await show_cart(callback, session, user)


@router.callback_query(F.data.startswith("cart_add:"))
async def add_to_cart(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    """Добавить товар в корзину.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
        state: FSM контекст
    """
    parts = callback.data.split(":")
    product_id = int(parts[1])
    size = parts[2]
    quantity = int(parts[3])
    color = parts[4] if len(parts) > 4 else None

    cart_service = CartService(session)
    await cart_service.add_item(
        user_id=user.id,
        product_id=product_id,
        size=size,
        quantity=quantity,
        color=color,
    )
    await session.commit()

    # Очищаем состояние FSM
    await state.clear()

    await callback.answer(f"✓ Добавлено в корзину: {quantity} шт.")

    # Показываем сообщение с кнопками
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🛒 Перейти в корзину",
            callback_data="cart_view",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📦 Продолжить покупки",
            callback_data="catalog",
        )
    )

    text = (
        f"✅ <b>Товар добавлен в корзину!</b>\n\n"
        f"📏 Размер: {size.upper()}\n"
    )
    if color:
        text += f"🎨 Цвет: {color}\n"
    text += f"🔢 Количество: {quantity} шт."

    await callback.message.edit_text(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    logger.info(
        "Item added to cart",
        user_id=user.id,
        product_id=product_id,
        quantity=quantity,
    )


@router.callback_query(F.data == "cart_checkout")
async def start_checkout(
    callback: CallbackQuery,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    """Начать оформление заказа из корзины.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        user: Пользователь
        state: FSM контекст
    """
    cart_service = CartService(session)
    cart_items = await cart_service.get_cart_items(user.id)

    if not cart_items:
        await callback.answer("❌ Корзина пуста", show_alert=True)
        return

    # Подсчитываем общую сумму
    total_price = Decimal("0")
    total_quantity = 0
    for item in cart_items:
        if item.product:
            total_price += item.product.price * item.quantity
            total_quantity += item.quantity

    # Сохраняем информацию о корзине в FSM
    await state.update_data(
        checkout_from_cart=True,
        total_price=float(total_price),
        total_quantity=total_quantity,
    )

    text = (
        "🛒 <b>Оформление заказа</b>\n\n"
        f"📦 Товаров: {len(cart_items)} шт. ({total_quantity} ед.)\n"
        f"💰 Итого: {total_price:,.2f} ₽\n\n"
        "Поделитесь вашим контактом для связи:\n"
        "• Нажмите кнопку ниже чтобы поделиться номером телефона\n"
        "• Или введите контакт вручную (телефон, username, email)"
    )

    keyboard = get_contact_request_keyboard()

    await callback.message.delete()
    await callback.message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(CheckoutStates.ENTER_CONTACT)
    await callback.answer()

    logger.info(
        "Checkout started from cart",
        user_id=user.id,
        items_count=len(cart_items),
    )


@router.message(CheckoutStates.ENTER_CONTACT, F.contact)
async def process_checkout_contact_shared(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка переданного контакта через RequestContact для checkout.

    Args:
        message: Message с контактом
        session: Сессия БД
        state: FSM контекст
    """
    contact = message.contact
    phone = contact.phone_number

    # Сохраняем контакт
    await state.update_data(customer_contact=phone)

    # Переходим к подтверждению
    await show_checkout_confirmation(message, session, state)


@router.message(CheckoutStates.ENTER_CONTACT, F.text == "✏️ Ввести вручную")
async def request_manual_contact_checkout(
    message: Message,
    state: FSMContext,
) -> None:
    """Запрос на ручной ввод контакта для checkout.

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


@router.message(CheckoutStates.ENTER_CONTACT, F.text == "❌ Отменить")
async def cancel_checkout(
    message: Message,
    state: FSMContext,
) -> None:
    """Отменить оформление заказа из корзины.

    Args:
        message: Message
        state: FSM контекст
    """
    await state.clear()

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Вернуться в корзину", callback_data="cart_view")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Продолжить покупки", callback_data="catalog")
    )

    text = (
        "❌ <b>Оформление заказа отменено</b>\n\n"
        "Ваша корзина сохранена."
    )

    await message.answer(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    logger.info("Checkout cancelled", user_id=message.from_user.id)


@router.message(CheckoutStates.ENTER_CONTACT, F.text)
async def process_manual_contact_checkout(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка контакта введенного вручную для checkout.

    Args:
        message: Message с контактом
        session: Сессия БД
        state: FSM контекст
    """
    contact = message.text.strip()

    if len(contact) < 5:
        await message.answer(
            "❌ Контакт слишком короткий. Введите корректный номер телефона, username или email."
        )
        return

    # Сохраняем контакт
    await state.update_data(customer_contact=contact)

    # Переходим к подтверждению
    await show_checkout_confirmation(message, session, state)


async def show_checkout_confirmation(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать экран подтверждения заказа из корзины.

    Args:
        message: Message
        session: Сессия БД
        state: FSM контекст
    """
    data = await state.get_data()
    contact = data.get("customer_contact", "—")
    total_price = data.get("total_price", 0)
    total_quantity = data.get("total_quantity", 0)

    # Получаем товары из корзины
    from src.database.models.user import User

    user_id = message.from_user.id
    result = await session.execute(
        __import__("sqlalchemy", fromlist=["select"]).select(User).where(
            User.telegram_id == user_id
        )
    )
    user = result.scalar_one_or_none()

    cart_service = CartService(session)
    cart_items = await cart_service.get_cart_items(user.id)

    text = (
        "✅ <b>Подтверждение заказа</b>\n\n"
        "Проверьте данные заказа:\n\n"
    )

    # Список товаров
    for i, item in enumerate(cart_items, 1):
        product = item.product
        if product:
            text += f"{i}. {item.display_name} × {item.quantity}\n"
            text += f"   💰 {(product.price * item.quantity):,.2f} ₽\n\n"

    text += f"━━━━━━━━━━━━━━━━\n"
    text += f"📦 Всего: {total_quantity} ед.\n"
    text += f"💰 <b>Итого: {total_price:,.2f} ₽</b>\n"
    text += f"📞 Контакт: {contact}\n\n"
    text += "Все верно?"

    # Создаем клавиатуру подтверждения
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить заказ",
            callback_data="checkout_confirm",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="checkout_cancel",
        )
    )

    await message.answer(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    await state.set_state(CheckoutStates.CONFIRM)


@router.callback_query(CheckoutStates.CONFIRM, F.data == "checkout_confirm")
async def confirm_and_create_orders(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Подтвердить и создать заказы из корзины.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
        user: Пользователь
    """
    data = await state.get_data()
    contact = data.get("customer_contact")

    if not contact:
        await callback.answer("❌ Ошибка данных заказа", show_alert=True)
        await state.clear()
        return

    # Получаем товары из корзины
    cart_service = CartService(session)
    cart_items = await cart_service.get_cart_items(user.id)

    if not cart_items:
        await callback.answer("❌ Корзина пуста", show_alert=True)
        await state.clear()
        return

    # Создаем ОДИН заказ с несколькими товарами
    order_service = OrderService(session)

    try:
        # Подготавливаем данные товаров для заказа
        items_data = [
            {
                "product_id": item.product_id,
                "size": item.size,
                "color": item.color,
                "quantity": item.quantity,
            }
            for item in cart_items
        ]

        # Создаем один заказ со всеми товарами
        order = await order_service.create_order_with_items(
            user_id=user.id,
            customer_contact=contact,
            items=items_data,
        )

        await session.commit()

        # Получаем настройки платежей для альтернативного контакта
        from src.database.models.payment_settings import PaymentSettings
        payment_settings = await PaymentSettings.get_current_settings(session)
        alternative_contact = payment_settings.alternative_contact_username if payment_settings else None

        # Уведомляем пользователя о заказе
        await NotificationService.notify_user_order_created(callback.bot, order, alternative_contact)
        # Уведомляем админов
        await NotificationService.notify_admins_new_order(callback.bot, order)

        # Очищаем корзину после успешного оформления
        await cart_service.clear_cart(user.id)
        await session.commit()

        text = (
            f"✅ <b>Заказ оформлен!</b>\n\n"
            f"📋 Номер заказа: #{order.id}\n"
            f"📦 Товаров в заказе: {order.total_items}\n"
            f"💰 Общая сумма: {order.total_price:,.2f} ₽\n\n"
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
            "Order created from cart",
            user_id=user.id,
            order_id=order.id,
            items_count=order.total_items,
        )

    except Exception as e:
        logger.error(
            "Failed to create orders from cart",
            user_id=user.id,
            error=str(e),
            exc_info=True,
        )
        await callback.answer(
            "❌ Ошибка создания заказов. Попробуйте позже.",
            show_alert=True,
        )
        await state.clear()


@router.callback_query(CheckoutStates.CONFIRM, F.data == "checkout_cancel")
async def cancel_from_confirmation_checkout(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Отменить заказ на этапе подтверждения checkout.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await state.clear()

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Вернуться в корзину", callback_data="cart_view")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Продолжить покупки", callback_data="catalog")
    )

    text = (
        "❌ <b>Заказ отменён</b>\n\n"
        "Ваша корзина сохранена."
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    await callback.answer()
    logger.info("Checkout cancelled at confirmation", user_id=callback.from_user.id)


# ==============================================
# БЫСТРЫЙ ЗАКАЗ (без добавления в корзину)
# ==============================================

@router.callback_query(F.data.startswith("quick_order:"))
async def start_quick_order(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Начать быстрый заказ товара (без корзины).

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    parts = callback.data.split(":")
    product_id = int(parts[1])
    size = parts[2]
    quantity = int(parts[3])
    color = parts[4] if len(parts) > 4 else None

    # Получаем информацию о товаре
    from src.services.product_service import ProductService

    product_service = ProductService(session)
    product = await product_service.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    # Сохраняем данные заказа в FSM
    await state.update_data(
        quick_order=True,
        product_id=product_id,
        product_name=product.name,
        product_price=product.formatted_price,
        size=size,
        quantity=quantity,
        color=color,
    )

    total_price = product.price * quantity

    text = (
        "✅ <b>Быстрый заказ</b>\n\n"
        f"📦 Товар: {product.name}\n"
        f"💰 Цена: {product.formatted_price}\n"
    )

    if color:
        text += f"🎨 Цвет: {color}\n"

    text += (
        f"📏 Размер: {size.upper()}\n"
        f"🔢 Количество: {quantity} шт.\n"
        f"💵 Итого: {total_price:,.2f} ₽\n\n"
        "Поделитесь вашим контактом для связи:\n"
        "• Нажмите кнопку ниже чтобы поделиться номером телефона\n"
        "• Или введите контакт вручную (телефон, username, email)"
    )

    keyboard = get_contact_request_keyboard()

    await callback.message.delete()
    await callback.message.answer(
        text=text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await state.set_state(QuickOrderStates.ENTER_CONTACT)
    await callback.answer()

    logger.info(
        "Quick order started",
        user_id=callback.from_user.id,
        product_id=product_id,
        quantity=quantity,
    )


@router.message(QuickOrderStates.ENTER_CONTACT, F.contact)
async def process_quick_order_contact_shared(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка переданного контакта для быстрого заказа.

    Args:
        message: Message с контактом
        session: Сессия БД
        state: FSM контекст
    """
    contact = message.contact
    phone = contact.phone_number

    # Сохраняем контакт
    await state.update_data(customer_contact=phone)

    # Переходим к подтверждению
    await show_quick_order_confirmation(message, session, state)


@router.message(QuickOrderStates.ENTER_CONTACT, F.text == "✏️ Ввести вручную")
async def request_manual_contact_quick_order(
    message: Message,
    state: FSMContext,
) -> None:
    """Запрос на ручной ввод контакта для быстрого заказа.

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


@router.message(QuickOrderStates.ENTER_CONTACT, F.text == "❌ Отменить")
async def cancel_quick_order(
    message: Message,
    state: FSMContext,
) -> None:
    """Отменить быстрый заказ.

    Args:
        message: Message
        state: FSM контекст
    """
    await state.clear()

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📦 Вернуться в каталог", callback_data="catalog")
    )
    builder.row(
        InlineKeyboardButton(text="🛒 Корзина", callback_data="cart_view")
    )

    text = (
        "❌ <b>Заказ отменён</b>\n\n"
        "Вы можете продолжить покупки."
    )

    await message.answer(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    logger.info("Quick order cancelled", user_id=message.from_user.id)


@router.message(QuickOrderStates.ENTER_CONTACT, F.text)
async def process_manual_contact_quick_order(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка контакта введенного вручную для быстрого заказа.

    Args:
        message: Message с контактом
        session: Сессия БД
        state: FSM контекст
    """
    contact = message.text.strip()

    if len(contact) < 5:
        await message.answer(
            "❌ Контакт слишком короткий. Введите корректный номер телефона, username или email."
        )
        return

    # Сохраняем контакт
    await state.update_data(customer_contact=contact)

    # Переходим к подтверждению
    await show_quick_order_confirmation(message, session, state)


async def show_quick_order_confirmation(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать экран подтверждения быстрого заказа.

    Args:
        message: Message
        session: Сессия БД
        state: FSM контекст
    """
    data = await state.get_data()

    product_name = data.get("product_name", "Товар")
    product_price = data.get("product_price", "—")
    size = data.get("size", "—")
    quantity = data.get("quantity", 1)
    color = data.get("color")
    contact = data.get("customer_contact", "—")
    product_id = data.get("product_id")

    # Получаем товар для расчета итоговой цены
    from src.services.product_service import ProductService

    product_service = ProductService(session)
    product = await product_service.get_product(product_id)

    total_price = product.price * quantity if product else 0

    text = (
        "✅ <b>Подтверждение заказа</b>\n\n"
        "Проверьте данные заказа:\n\n"
        f"📦 Товар: {product_name}\n"
        f"💰 Цена: {product_price}\n"
    )

    if color:
        text += f"🎨 Цвет: {color}\n"

    text += (
        f"📏 Размер: {size.upper()}\n"
        f"🔢 Количество: {quantity} шт.\n"
        f"💵 Итого: {total_price:,.2f} ₽\n"
        f"📞 Контакт: {contact}\n\n"
        "Все верно?"
    )

    # Создаем клавиатуру подтверждения
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить заказ",
            callback_data="quick_order_confirm",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="quick_order_cancel",
        )
    )

    await message.answer(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    await state.set_state(QuickOrderStates.CONFIRM)


@router.callback_query(QuickOrderStates.CONFIRM, F.data == "quick_order_confirm")
async def confirm_and_create_quick_order(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    user: User,
) -> None:
    """Подтвердить и создать быстрый заказ.

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

        # Получаем настройки платежей для альтернативного контакта
        from src.database.models.payment_settings import PaymentSettings
        payment_settings = await PaymentSettings.get_current_settings(session)
        alternative_contact = payment_settings.alternative_contact_username if payment_settings else None

        # Уведомляем пользователя
        await NotificationService.notify_user_order_created(callback.bot, order, alternative_contact)

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
            "Quick order created",
            user_id=user.id,
            order_id=order.id,
            product_id=product_id,
        )

    except Exception as e:
        logger.error(
            "Failed to create quick order",
            user_id=user.id,
            error=str(e),
            exc_info=True,
        )
        await callback.answer(
            "❌ Ошибка создания заказа. Попробуйте позже.",
            show_alert=True,
        )
        await state.clear()


@router.callback_query(QuickOrderStates.CONFIRM, F.data == "quick_order_cancel")
async def cancel_from_confirmation_quick_order(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Отменить заказ на этапе подтверждения быстрого заказа.

    Args:
        callback: CallbackQuery
        state: FSM контекст
    """
    await state.clear()

    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📦 Вернуться в каталог", callback_data="catalog")
    )
    builder.row(
        InlineKeyboardButton(text="🛒 Корзина", callback_data="cart_view")
    )

    text = (
        "❌ <b>Заказ отменён</b>\n\n"
        "Вы можете продолжить покупки."
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    await callback.answer()
    logger.info("Quick order cancelled at confirmation", user_id=callback.from_user.id)
