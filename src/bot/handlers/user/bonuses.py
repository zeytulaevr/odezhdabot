"""Хендлеры для работы с бонусной системой пользователя."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.bot_settings import BotSettings
from src.database.models.user import User
from src.services.bonus_service import BonusService

logger = get_logger(__name__)

router = Router(name="user_bonuses")


@router.callback_query(F.data == "user:bonuses")
async def show_bonuses(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать информацию о бонусах пользователя.

    Args:
        callback: Callback query
        user: Пользователь из БД
        session: Сессия БД
        state: FSM контекст
    """
    logger.info("User bonuses view", user_id=user.id)

    # Очищаем состояние
    await state.clear()

    # Получаем настройки
    settings = await BotSettings.get_settings(session)

    # Проверяем, включена ли бонусная система
    if not settings.bonus_enabled:
        await callback.answer(
            "⚠️ Бонусная система временно недоступна",
            show_alert=True,
        )
        return

    # Получаем информацию о бонусах
    bonus_service = BonusService(session)
    balance = await bonus_service.get_user_bonus_balance(user.id)

    # Получаем последние транзакции
    transactions = await bonus_service.get_user_transactions(user.id, limit=5)

    # Формируем сообщение
    text = (
        "🎁 <b>Ваши бонусы</b>\n\n"
        f"💰 Баланс: <b>{balance} бонусов</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Начисление: <b>{settings.bonus_purchase_percent}%</b> от суммы заказа\n"
        f"💳 Можно оплатить до <b>{settings.bonus_max_payment_percent}%</b> заказа\n"
        f"🛒 Минимальная сумма: <b>{settings.bonus_min_order_amount} ₽</b>\n\n"
    )

    if transactions:
        text += "📜 <b>Последние операции:</b>\n\n"
        for tx in transactions:
            # Форматируем тип операции
            type_emoji = {
                "purchase": "🛍",
                "promocode": "🎟",
                "admin_grant": "👨‍💼",
                "payment": "💳",
                "refund": "↩️",
            }.get(tx.transaction_type, "•")

            # Форматируем сумму
            amount_str = f"+{tx.amount}" if tx.amount > 0 else str(tx.amount)

            text += (
                f"{type_emoji} <code>{amount_str}</code> "
                f"(баланс: {tx.balance_after})\n"
            )
            if tx.description:
                text += f"   <i>{tx.description}</i>\n"

        text += "\n"
    else:
        text += "📜 <i>Пока нет операций с бонусами</i>\n\n"

    text += "💡 <i>Бонусы начисляются автоматически после оплаты заказа</i>"

    # Создаём клавиатуру
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎟 Активировать промокод",
            callback_data="user:bonuses:activate_promocode",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="📜 История операций",
            callback_data="user:bonuses:history",
        )
    )

    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_menu",
        )
    )

    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "user:bonuses:activate_promocode")
async def start_promocode_activation(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать активацию промокода.

    Args:
        callback: Callback query
        state: FSM контекст
    """
    from aiogram.fsm.state import State, StatesGroup

    class BonusStates(StatesGroup):
        """Состояния для работы с бонусами."""
        ENTER_PROMOCODE = State()

    await state.set_state(BonusStates.ENTER_PROMOCODE)

    text = (
        "🎟 <b>Активация промокода</b>\n\n"
        "Введите промокод для активации:"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="user:bonuses",
        )
    )

    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(F.text)
async def process_promocode(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Обработка ввода промокода.

    Args:
        message: Сообщение
        user: Пользователь из БД
        session: Сессия БД
        state: FSM контекст
    """
    # Проверяем состояние
    current_state = await state.get_state()
    if not current_state or "ENTER_PROMOCODE" not in current_state:
        return

    code = message.text.strip().upper()

    try:
        bonus_service = BonusService(session)
        transaction, promocode = await bonus_service.activate_promocode(user.id, code)

        await session.commit()

        await message.answer(
            f"✅ <b>Промокод активирован!</b>\n\n"
            f"🎁 Начислено: <b>{promocode.bonus_amount} бонусов</b>\n"
            f"💰 Новый баланс: <b>{transaction.balance_after} бонусов</b>",
            parse_mode="HTML",
        )

        # Возвращаемся к просмотру бонусов
        await state.clear()

        # Создаем фейковый callback для вызова show_bonuses
        fake_callback = type('obj', (object,), {
            'data': 'user:bonuses',
            'from_user': message.from_user,
            'message': message,
            'bot': message.bot,
            'answer': lambda text="", show_alert=False: message.answer(text) if text else None,
        })()

        await show_bonuses(fake_callback, user, session, state)

    except ValueError as e:
        await message.answer(
            f"❌ <b>Ошибка активации промокода</b>\n\n"
            f"{str(e)}",
            parse_mode="HTML",
        )


@router.callback_query(F.data == "user:bonuses:history")
async def show_bonus_history(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Показать полную историю бонусных операций.

    Args:
        callback: Callback query
        user: Пользователь из БД
        session: Сессия БД
    """
    logger.info("User bonus history view", user_id=user.id)

    bonus_service = BonusService(session)
    transactions = await bonus_service.get_user_transactions(user.id, limit=20)

    if not transactions:
        text = (
            "📜 <b>История бонусов</b>\n\n"
            "У вас пока нет операций с бонусами"
        )
    else:
        text = "📜 <b>История бонусов</b>\n\n"

        for tx in transactions:
            # Форматируем дату
            date_str = tx.created_at.strftime("%d.%m.%Y %H:%M")

            # Форматируем тип операции
            type_names = {
                "purchase": "Покупка",
                "promocode": "Промокод",
                "admin_grant": "Начисление",
                "payment": "Оплата",
                "refund": "Возврат",
            }
            type_name = type_names.get(tx.transaction_type, tx.transaction_type)

            # Форматируем сумму
            amount_str = f"+{tx.amount}" if tx.amount > 0 else str(tx.amount)

            text += f"<b>{date_str}</b>\n"
            text += f"{type_name}: <code>{amount_str}</code>\n"
            if tx.description:
                text += f"<i>{tx.description}</i>\n"
            text += f"Баланс после: {tx.balance_after}\n\n"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="user:bonuses",
        )
    )

    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    await callback.answer()
