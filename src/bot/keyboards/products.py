"""Клавиатуры для управления товарами."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.database.models.category import Category
from src.database.models.product import Product


def get_categories_keyboard(categories: list[Category]) -> InlineKeyboardMarkup:
    """Клавиатура выбора категории.

    Args:
        categories: Список категорий

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    for category in categories:
        builder.row(
            InlineKeyboardButton(
                text=f"📁 {category.name}",
                callback_data=f"cat:{category.id}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="superadmin:menu")
    )

    return builder.as_markup()


def get_product_actions_keyboard(product_id: int, is_active: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура действий с товаром.

    Args:
        product_id: ID товара
        is_active: Активен ли товар

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Опубликовать в канал
    builder.row(
        InlineKeyboardButton(
            text="📢 Опубликовать в канал",
            callback_data=f"prod_publish:{product_id}",
        )
    )

    # Активировать/Деактивировать
    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="❌ Деактивировать",
                callback_data=f"prod_deactivate:{product_id}",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Активировать",
                callback_data=f"prod_activate:{product_id}",
            )
        )

    # Удалить
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"prod_delete:{product_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="superadmin:menu")
    )

    return builder.as_markup()


def get_products_list_keyboard(
    products: list[Product], page: int = 0, total_pages: int = 1
) -> InlineKeyboardMarkup:
    """Клавиатура списка товаров.

    Args:
        products: Список товаров
        page: Текущая страница
        total_pages: Всего страниц

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    for product in products:
        status = "✅" if product.is_active else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {product.name} - {product.formatted_price}",
                callback_data=f"prod_view:{product.id}",
            )
        )

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"prod_page:{page-1}")
        )

    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop")
    )

    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"prod_page:{page+1}")
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="superadmin:menu")
    )

    return builder.as_markup()


def get_products_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню управления товарами.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить товар (диалог)",
            callback_data="prod_add_dialog",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📤 Загрузить из файла",
            callback_data="prod_upload_file",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📋 Список товаров",
            callback_data="products_list",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📁 Управление категориями",
            callback_data="categories_manage",
        )
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back"),
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="superadmin:menu"),
    )

    return builder.as_markup()


def get_confirm_delete_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления.

    Args:
        product_id: ID товара

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"prod_delete_confirm:{product_id}",
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"prod_view:{product_id}",
        ),
    )

    return builder.as_markup()


def get_order_button(product_id: int) -> InlineKeyboardMarkup:
    """Кнопка заказа для поста в канале.

    Args:
        product_id: ID товара

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🛒 Заказать",
            callback_data=f"order:{product_id}",
        )
    )

    return builder.as_markup()


def get_categories_manage_keyboard(
    categories: list[Category],
) -> InlineKeyboardMarkup:
    """Клавиатура управления категориями.

    Args:
        categories: Список категорий

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    for category in categories:
        status = "✅" if category.is_active else "❌"
        thread_status = "🔗" if category.thread_id else "❓"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {thread_status} {category.name}",
                callback_data=f"cat_view:{category.id}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить категорию",
            callback_data="cat_add",
        )
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="superadmin:menu")
    )

    return builder.as_markup()


def get_category_actions_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с категорией.

    Args:
        category_id: ID категории

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить название",
            callback_data=f"cat_rename:{category_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔗 Привязать к теме",
            callback_data=f"cat_thread_menu:{category_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить категорию",
            callback_data=f"cat_delete:{category_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data="back")
    )

    builder.row(
        InlineKeyboardButton(text="🏠 В меню", callback_data="superadmin:menu")
    )

    return builder.as_markup()


def get_thread_link_method_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора способа привязки темы.

    Args:
        category_id: ID категории

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🆕 Создать новую тему",
            callback_data=f"cat_thread_create:{category_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔢 Ввести thread_id вручную",
            callback_data=f"cat_thread_manual:{category_id}",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"cat_view:{category_id}",
        )
    )

    return builder.as_markup()


def get_thread_color_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора цвета иконки темы.

    Args:
        category_id: ID категории

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    colors = [
        ("🔵 Синий", "blue"),
        ("🟡 Желтый", "yellow"),
        ("🟣 Фиолетовый", "purple"),
        ("🟢 Зеленый", "green"),
        ("🌸 Розовый", "pink"),
        ("🔴 Красный", "red"),
    ]

    for text, color in colors:
        builder.row(
            InlineKeyboardButton(
                text=text,
                callback_data=f"cat_thread_color:{category_id}:{color}",
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"cat_thread_menu:{category_id}",
        )
    )

    return builder.as_markup()
