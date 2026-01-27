"""FSM States для управления настройками бота."""

from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    """Состояния для управления настройками."""

    # Бонусная система
    ENTER_BONUS_PURCHASE_PERCENT = State()
    ENTER_BONUS_MAX_PAYMENT_PERCENT = State()
    ENTER_BONUS_MIN_ORDER_AMOUNT = State()

    # Платежи
    ENTER_PAYMENT_DETAILS = State()
    ENTER_PAYMENT_INSTRUCTIONS = State()
    ENTER_ALTERNATIVE_CONTACT = State()

    # Заказы
    ENTER_MIN_ORDER_AMOUNT = State()
    ENTER_MAX_ITEMS_PER_ORDER = State()
    ENTER_MAX_QUANTITY_PER_ITEM = State()

    # Уведомления
    ENTER_WELCOME_MESSAGE = State()
    ENTER_HELP_MESSAGE = State()
    ENTER_LARGE_ORDER_MESSAGE = State()

    # Каталог
    ENTER_PRODUCTS_PER_PAGE = State()
