"""Главные меню и панели для разных ролей пользователей (inline клавиатуры)."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =======================
# Главное меню пользователя
# =======================
def get_user_menu() -> InlineKeyboardMarkup:
    """Главное меню для обычного пользователя (inline)."""
    builder = InlineKeyboardBuilder()

    # Первый ряд
    builder.row(
        InlineKeyboardButton(text="📦 Каталог", callback_data="catalog"),
        InlineKeyboardButton(text="🛍 Мои заказы", callback_data="my_orders"),
    )

    # Второй ряд
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="user:help"),
    )

    return builder.as_markup()


# =======================
# Главное меню администратора
# =======================
def get_admin_menu() -> InlineKeyboardMarkup:
    """Главное меню для администратора (inline)."""
    builder = InlineKeyboardBuilder()

    # Первый ряд
    builder.row(
        InlineKeyboardButton(text="📋 Заказы", callback_data="admin:orders"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
    )

    # Второй ряд
    builder.row(
        InlineKeyboardButton(text="👤 Пользователи", callback_data="admin:users"),
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="admin:help"),
    )

    return builder.as_markup()


# =======================
# Главное меню супер-администратора
# =======================
def get_superadmin_menu() -> InlineKeyboardMarkup:
    """Главное меню для супер-администратора (inline)."""
    builder = InlineKeyboardBuilder()

    # Первый ряд
    builder.row(
        InlineKeyboardButton(text="📋 Заказы", callback_data="superadmin:orders"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="superadmin:stats"),
    )

    # Второй ряд
    builder.row(
        InlineKeyboardButton(text="📦 Товары", callback_data="superadmin:products"),
        InlineKeyboardButton(text="👤 Пользователи", callback_data="superadmin:users"),
    )

    # Третий ряд
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="superadmin:broadcast"),
        InlineKeyboardButton(text="🔧 Модерация", callback_data="superadmin:moderation"),
    )

    # Четвёртый ряд
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="superadmin:settings"),
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="superadmin:help"),
    )

    return builder.as_markup()


# =======================
# Админ-панель
# =======================
def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Inline клавиатура для админ-панели."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Новые заказы", callback_data="admin:orders:new"),
        InlineKeyboardButton(text="🔄 В обработке", callback_data="admin:orders:processing"),
        InlineKeyboardButton(text="✅ Завершённые", callback_data="admin:orders:completed"),
    )

    builder.row(
        InlineKeyboardButton(text="━━━━━━━━━━━━━━━", callback_data="separator"),
    )

    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
        InlineKeyboardButton(text="👤 Пользователи", callback_data="admin:users"),
    )

    return builder.as_markup()


# =======================
# Супер-админ панель
# =======================
def get_superadmin_panel_keyboard() -> InlineKeyboardMarkup:
    """Inline клавиатура супер-админ панели."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Заказы", callback_data="superadmin:orders"),
        InlineKeyboardButton(text="📦 Товары", callback_data="superadmin:products"),
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="superadmin:products:add"),
        InlineKeyboardButton(text="🏷 Категории", callback_data="superadmin:categories"),
    )

    builder.row(
        InlineKeyboardButton(text="━━━━━━━━━━━━━━━", callback_data="separator"),
    )

    builder.row(
        InlineKeyboardButton(text="🔧 Модерация отзывов", callback_data="superadmin:reviews"),
        InlineKeyboardButton(text="📢 Рассылка", callback_data="superadmin:broadcast"),
    )

    builder.row(
        InlineKeyboardButton(text="👤 Пользователи", callback_data="superadmin:users"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="superadmin:settings"),
    )

    return builder.as_markup()


# =======================
# Кнопка "Назад"
# =======================
def get_back_button(callback_data: str = "back") -> InlineKeyboardMarkup:
    """Inline клавиатура с кнопкой 'Назад'."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data),
    )
    return builder.as_markup()
