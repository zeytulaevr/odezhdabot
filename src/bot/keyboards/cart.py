"""Клавиатуры для работы с корзиной."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.models.cart import CartItem


def get_add_to_cart_keyboard(
    product_id: int, size: str, quantity: int, color: str | None = None
) -> InlineKeyboardMarkup:
    """Клавиатура выбора действия после конфигурации товара.

    Args:
        product_id: ID товара
        size: Выбранный размер
        quantity: Выбранное количество
        color: Выбранный цвет (опционально)

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Формируем callback_data с учетом цвета
    add_cart_data = f"cart_add:{product_id}:{size}:{quantity}"
    quick_order_data = f"quick_order:{product_id}:{size}:{quantity}"
    if color:
        add_cart_data += f":{color}"
        quick_order_data += f":{color}"

    # Два логичных варианта: добавить в корзину или заказать сразу
    builder.row(
        InlineKeyboardButton(
            text="🛒 Добавить в корзину",
            callback_data=add_cart_data,
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="✅ Заказать сейчас",
            callback_data=quick_order_data,
        )
    )

    return builder.as_markup()


def get_cart_added_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после добавления товара в корзину.

    Returns:
        Inline клавиатура
    """
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

    return builder.as_markup()


def get_cart_view_keyboard(cart_items: list[CartItem]) -> InlineKeyboardMarkup:
    """Клавиатура просмотра корзины.

    Args:
        cart_items: Товары в корзине

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Кнопки для каждого товара
    for item in cart_items:
        builder.row(
            InlineKeyboardButton(
                text=f"{item.display_name} - {item.quantity} шт.",
                callback_data=f"cart_item:{item.id}",
            )
        )

    if cart_items:
        # Кнопка оформления заказа
        builder.row(
            InlineKeyboardButton(
                text="✅ Оформить заказ",
                callback_data="cart_checkout",
            )
        )
        # Кнопка очистки корзины
        builder.row(
            InlineKeyboardButton(
                text="🗑 Очистить корзину",
                callback_data="cart_clear",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="📦 Продолжить покупки",
            callback_data="catalog",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="back_to_menu",
        )
    )

    return builder.as_markup()


def get_cart_item_keyboard(cart_item_id: int, current_quantity: int) -> InlineKeyboardMarkup:
    """Клавиатура управления товаром в корзине.

    Args:
        cart_item_id: ID товара в корзине
        current_quantity: Текущее количество

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Кнопки изменения количества
    row_buttons = []

    # Кнопка уменьшения (минус)
    if current_quantity > 1:
        row_buttons.append(
            InlineKeyboardButton(
                text="➖",
                callback_data=f"cart_qty:{cart_item_id}:minus",
            )
        )

    # Показываем текущее количество
    row_buttons.append(
        InlineKeyboardButton(
            text=f"{current_quantity} шт.",
            callback_data="noop",
        )
    )

    # Кнопка увеличения (плюс)
    if current_quantity < 99:  # Максимум 99 шт
        row_buttons.append(
            InlineKeyboardButton(
                text="➕",
                callback_data=f"cart_qty:{cart_item_id}:plus",
            )
        )

    builder.row(*row_buttons)

    # Кнопка удаления товара
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить из корзины",
            callback_data=f"cart_remove:{cart_item_id}",
        )
    )

    # Кнопка назад к корзине
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к корзине",
            callback_data="cart_view",
        )
    )

    return builder.as_markup()


def get_cart_clear_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения очистки корзины.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, очистить",
            callback_data="cart_clear_confirm",
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cart_view",
        ),
    )

    return builder.as_markup()
