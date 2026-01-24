"""Обработчики корзины покупок."""

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.cart import (
    get_cart_clear_confirm_keyboard,
    get_cart_item_keyboard,
    get_cart_view_keyboard,
)
from src.core.logging import get_logger
from src.database.models.user import User
from src.services.cart_service import CartService

logger = get_logger(__name__)

router = Router(name="user_cart")


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
    from aiogram.fsm.state import State, StatesGroup

    class CheckoutStates(StatesGroup):
        """Состояния оформления заказа из корзины."""
        ENTER_CONTACT = State()

    cart_service = CartService(session)
    cart_items = await cart_service.get_cart_items(user.id)

    if not cart_items:
        await callback.answer("❌ Корзина пуста", show_alert=True)
        return

    # Сохраняем информацию о корзине в FSM
    await state.update_data(checkout_from_cart=True)

    text = (
        "🛒 <b>Оформление заказа</b>\n\n"
        f"📦 Товаров в корзине: {len(cart_items)} шт.\n\n"
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


# Временный хендлер для завершения checkout (будет расширен позже)
@router.message(lambda message: message.text and message.text.startswith("+"))
async def process_checkout_contact(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
) -> None:
    """Временный обработчик контакта для checkout."""
    await message.answer(
        "✅ Функционал оформления заказа из корзины будет доработан в следующей версии.\n"
        "Пока используйте оформление отдельных товаров через каталог.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.clear()
