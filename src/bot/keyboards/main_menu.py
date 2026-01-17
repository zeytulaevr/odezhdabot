"""Главные меню для разных ролей пользователей."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_user_menu() -> ReplyKeyboardMarkup:
    """Получить главное меню для обычного пользователя.

    Returns:
        Reply клавиатура для пользователя
    """
    builder = ReplyKeyboardBuilder()

    # Первый ряд
    builder.row(
        InlineKeyboardButton(text="📦 Каталог"),
        InlineKeyboardButton(text="🛍 Мои заказы"),
    )

    # Второй ряд
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь"),
    )

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел...",
    )


def get_admin_menu() -> ReplyKeyboardMarkup:
    """Получить главное меню для администратора.

    Returns:
        Reply клавиатура для администратора
    """
    builder = ReplyKeyboardBuilder()

    # Первый ряд - основные функции
    builder.row(
        InlineKeyboardButton(text="📋 Заказы"),
        InlineKeyboardButton(text="📊 Статистика"),
    )

    # Второй ряд
    builder.row(
        InlineKeyboardButton(text="👤 Пользователи"),
        InlineKeyboardButton(text="ℹ️ Помощь"),
    )

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Панель администратора...",
    )


def get_superadmin_menu() -> ReplyKeyboardMarkup:
    """Получить главное меню для супер-администратора.

    Returns:
        Reply клавиатура для супер-администратора
    """
    builder = ReplyKeyboardBuilder()

    # Первый ряд - заказы и статистика
    builder.row(
        InlineKeyboardButton(text="📋 Заказы"),
        InlineKeyboardButton(text="📊 Статистика"),
    )

    # Второй ряд - управление
    builder.row(
        InlineKeyboardButton(text="📦 Товары"),
        InlineKeyboardButton(text="👤 Пользователи"),
    )

    # Третий ряд - дополнительные функции
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка"),
        InlineKeyboardButton(text="🔧 Модерация"),
    )

    # Четвёртый ряд
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки"),
        InlineKeyboardButton(text="ℹ️ Помощь"),
    )

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Панель супер-администратора...",
    )


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Получить inline клавиатуру админ-панели.

    Returns:
        Inline клавиатура с кнопками админ-панели
    """
    builder = InlineKeyboardBuilder()

    # Управление заказами
    builder.row(
        InlineKeyboardButton(text="📋 Новые заказы", callback_data="admin:orders:new"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 В обработке", callback_data="admin:orders:processing"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Завершённые", callback_data="admin:orders:completed"),
    )

    # Разделитель
    builder.row(
        InlineKeyboardButton(text="━━━━━━━━━━━━━━━", callback_data="separator"),
    )

    # Статистика
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
    )

    # Пользователи
    builder.row(
        InlineKeyboardButton(text="👤 Пользователи", callback_data="admin:users"),
    )

    return builder.as_markup()


def get_superadmin_panel_keyboard() -> InlineKeyboardMarkup:
    """Получить inline клавиатуру супер-админ панели.

    Returns:
        Inline клавиатура с кнопками супер-админ панели
    """
    builder = InlineKeyboardBuilder()

    # Управление заказами
    builder.row(
        InlineKeyboardButton(text="📋 Заказы", callback_data="superadmin:orders"),
    )

    # Управление товарами
    builder.row(
        InlineKeyboardButton(text="📦 Товары", callback_data="superadmin:products"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="superadmin:products:add"),
    )

    # Управление категориями
    builder.row(
        InlineKeyboardButton(text="🏷 Категории", callback_data="superadmin:categories"),
    )

    # Разделитель
    builder.row(
        InlineKeyboardButton(text="━━━━━━━━━━━━━━━", callback_data="separator"),
    )

    # Модерация
    builder.row(
        InlineKeyboardButton(text="🔧 Модерация отзывов", callback_data="superadmin:reviews"),
    )

    # Рассылка
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="superadmin:broadcast"),
    )

    # Пользователи
    builder.row(
        InlineKeyboardButton(text="👤 Пользователи", callback_data="superadmin:users"),
    )

    # Настройки
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="superadmin:settings"),
    )

    return builder.as_markup()


def get_back_button(callback_data: str = "back") -> InlineKeyboardMarkup:
    """Получить клавиатуру с кнопкой "Назад".

    Args:
        callback_data: Callback data для кнопки

    Returns:
        Inline клавиатура с кнопкой назад
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data),
    )
    return builder.as_markup()
