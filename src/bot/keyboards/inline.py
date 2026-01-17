"""Inline клавиатуры бота."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.core.constants import Buttons, CallbackPrefix, ProductCategory, ProductSize


def get_catalog_keyboard() -> InlineKeyboardMarkup:
    """Получить клавиатуру каталога с категориями.

    Returns:
        Inline клавиатура с категориями товаров
    """
    builder = InlineKeyboardBuilder()

    # Все товары
    builder.row(
        InlineKeyboardButton(
            text=Buttons.ALL_PRODUCTS,
            callback_data=f"{CallbackPrefix.CATEGORY}:all",
        )
    )

    # Категории товаров
    categories = [
        ("👕 Футболки", ProductCategory.TSHIRTS),
        ("🧥 Худи", ProductCategory.HOODIES),
        ("🧥 Куртки", ProductCategory.JACKETS),
        ("👖 Брюки", ProductCategory.PANTS),
        ("👟 Обувь", ProductCategory.SHOES),
        ("🎒 Аксессуары", ProductCategory.ACCESSORIES),
    ]

    for text, category in categories:
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"{CallbackPrefix.CATEGORY}:{category.value}",
            )
        )

    # Кнопка назад
    builder.row(
        InlineKeyboardButton(text=Buttons.BACK, callback_data=CallbackPrefix.BACK)
    )

    return builder.as_markup()


def get_product_keyboard(product_id: int, in_cart: bool = False) -> InlineKeyboardMarkup:
    """Получить клавиатуру для товара.

    Args:
        product_id: ID товара
        in_cart: Находится ли товар уже в корзине

    Returns:
        Inline клавиатура для товара
    """
    builder = InlineKeyboardBuilder()

    if not in_cart:
        builder.row(
            InlineKeyboardButton(
                text=Buttons.ADD_TO_CART,
                callback_data=f"{CallbackPrefix.ADD_TO_CART}:{product_id}",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text=Buttons.BUY_NOW,
                callback_data=f"{CallbackPrefix.PRODUCT}:buy:{product_id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Уже в корзине",
                callback_data=f"{CallbackPrefix.PRODUCT}:info:{product_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(text=Buttons.BACK, callback_data=CallbackPrefix.BACK)
    )

    return builder.as_markup()


def get_size_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Получить клавиатуру выбора размера.

    Args:
        product_id: ID товара

    Returns:
        Inline клавиатура с размерами
    """
    builder = InlineKeyboardBuilder()

    # Размеры
    sizes = [ProductSize.XS, ProductSize.S, ProductSize.M, ProductSize.L, ProductSize.XL, ProductSize.XXL]

    # Добавляем размеры по 3 в ряд
    for i in range(0, len(sizes), 3):
        row_buttons = []
        for size in sizes[i:i+3]:
            row_buttons.append(
                InlineKeyboardButton(
                    text=size.value.upper(),
                    callback_data=f"{CallbackPrefix.SIZE}:{product_id}:{size.value}",
                )
            )
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(text=Buttons.BACK, callback_data=CallbackPrefix.BACK)
    )

    return builder.as_markup()


def get_quantity_keyboard(product_id: int, max_quantity: int = 10) -> InlineKeyboardMarkup:
    """Получить клавиатуру выбора количества.

    Args:
        product_id: ID товара
        max_quantity: Максимальное количество

    Returns:
        Inline клавиатура с количеством
    """
    builder = InlineKeyboardBuilder()

    # Количество
    quantities = list(range(1, min(max_quantity + 1, 11)))

    # Добавляем количество по 5 в ряд
    for i in range(0, len(quantities), 5):
        row_buttons = []
        for qty in quantities[i:i+5]:
            row_buttons.append(
                InlineKeyboardButton(
                    text=str(qty),
                    callback_data=f"{CallbackPrefix.QUANTITY}:{product_id}:{qty}",
                )
            )
        builder.row(*row_buttons)

    builder.row(
        InlineKeyboardButton(text=Buttons.BACK, callback_data=CallbackPrefix.BACK)
    )

    return builder.as_markup()


def get_cart_keyboard(has_items: bool = True) -> InlineKeyboardMarkup:
    """Получить клавиатуру корзины.

    Args:
        has_items: Есть ли товары в корзине

    Returns:
        Inline клавиатура корзины
    """
    builder = InlineKeyboardBuilder()

    if has_items:
        builder.row(
            InlineKeyboardButton(
                text=Buttons.CHECKOUT,
                callback_data=f"{CallbackPrefix.ORDER}:checkout",
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🗑 Очистить корзину",
                callback_data=f"{CallbackPrefix.CART}:clear",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text=Buttons.CATALOG,
            callback_data=f"{CallbackPrefix.CATEGORY}:all",
        )
    )

    return builder.as_markup()


def get_order_keyboard(order_id: int, can_cancel: bool = True) -> InlineKeyboardMarkup:
    """Получить клавиатуру заказа.

    Args:
        order_id: ID заказа
        can_cancel: Можно ли отменить заказ

    Returns:
        Inline клавиатура заказа
    """
    builder = InlineKeyboardBuilder()

    if can_cancel:
        builder.row(
            InlineKeyboardButton(
                text="❌ Отменить заказ",
                callback_data=f"{CallbackPrefix.ORDER}:cancel:{order_id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="📋 Мои заказы",
            callback_data=f"{CallbackPrefix.ORDER}:list",
        )
    )

    return builder.as_markup()


def get_pagination_keyboard(
    prefix: str,
    current_page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Получить клавиатуру пагинации.

    Args:
        prefix: Префикс callback_data
        current_page: Текущая страница
        total_pages: Всего страниц

    Returns:
        Inline клавиатура пагинации
    """
    builder = InlineKeyboardBuilder()

    buttons = []

    # Кнопка "назад"
    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"{CallbackPrefix.PAGE}:{prefix}:{current_page - 1}",
            )
        )

    # Текущая страница
    buttons.append(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data=f"{CallbackPrefix.PAGE}:current",
        )
    )

    # Кнопка "вперед"
    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"{CallbackPrefix.PAGE}:{prefix}:{current_page + 1}",
            )
        )

    builder.row(*buttons)

    return builder.as_markup()
