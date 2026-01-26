"""Клавиатуры для управления настройками бота."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_settings_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню настроек.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    # Первый ряд - Бонусная система
    builder.row(
        InlineKeyboardButton(
            text="🎁 Бонусная система",
            callback_data="settings:bonus",
        )
    )

    # Второй ряд - Платежи
    builder.row(
        InlineKeyboardButton(
            text="💳 Платежи",
            callback_data="settings:payment",
        )
    )

    # Третий ряд - Заказы
    builder.row(
        InlineKeyboardButton(
            text="📦 Заказы",
            callback_data="settings:orders",
        )
    )

    # Четвёртый ряд - Уведомления
    builder.row(
        InlineKeyboardButton(
            text="📬 Уведомления",
            callback_data="settings:notifications",
        )
    )

    # Пятый ряд - Каталог
    builder.row(
        InlineKeyboardButton(
            text="📚 Каталог",
            callback_data="settings:catalog",
        )
    )

    # Кнопка назад
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="superadmin:menu",
        )
    )

    return builder.as_markup()


def get_bonus_settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек бонусной системы.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📊 Процент начисления за покупку",
            callback_data="settings:bonus:purchase_percent",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="💰 Максимальный % оплаты бонусами",
            callback_data="settings:bonus:max_payment_percent",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🛒 Минимальная сумма для начисления",
            callback_data="settings:bonus:min_order_amount",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔄 Вкл/Выкл бонусную систему",
            callback_data="settings:bonus:toggle_enabled",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="settings:menu",
        )
    )

    return builder.as_markup()


def get_payment_settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек платежей.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💳 Реквизиты для оплаты",
            callback_data="settings:payment:details",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📝 Инструкции по оплате",
            callback_data="settings:payment:instructions",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="👤 Альтернативный контакт",
            callback_data="settings:payment:alternative_contact",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="settings:menu",
        )
    )

    return builder.as_markup()


def get_order_settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек заказов.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💵 Минимальная сумма заказа",
            callback_data="settings:orders:min_amount",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📦 Макс. товаров в заказе",
            callback_data="settings:orders:max_items",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🔢 Макс. количество одного товара",
            callback_data="settings:orders:max_quantity",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="settings:menu",
        )
    )

    return builder.as_markup()


def get_notification_settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек уведомлений.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="👋 Приветственное сообщение",
            callback_data="settings:notifications:welcome",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="ℹ️ Сообщение помощи",
            callback_data="settings:notifications:help",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📦 Сообщение о большом заказе",
            callback_data="settings:notifications:large_order",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="settings:menu",
        )
    )

    return builder.as_markup()


def get_catalog_settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек каталога.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📄 Товаров на странице",
            callback_data="settings:catalog:per_page",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="🖼 Вкл/Выкл товары без фото",
            callback_data="settings:catalog:toggle_without_photos",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="settings:menu",
        )
    )

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены.

    Returns:
        Inline клавиатура
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="settings:cancel",
        )
    )

    return builder.as_markup()
