"""Хендлер команды /start для обычных пользователей."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.main_menu import get_user_menu
from src.core.logging import get_logger
from src.database.models.user import User

logger = get_logger(__name__)

router = Router(name="user_start")


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(
    message: Message,
    user: User | None = None,
    session: AsyncSession | None = None,
    state: FSMContext | None = None,
) -> None:
    """Обработчик команды /start с deep link.

    Deep link формат: /start order_123
    Перенаправляет пользователя сразу к оформлению заказа.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
        session: Сессия БД
        state: FSM контекст
    """
    if not user:
        logger.error("User not found in start deep link handler")
        await message.answer("❌ Ошибка авторизации. Попробуйте позже.")
        return

    # Получаем параметр deep link
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else None

    if args and args.startswith("order_"):
        # Извлекаем ID товара
        try:
            product_id = int(args.split("_")[1])

            logger.info(
                "Deep link order start",
                user_id=user.id,
                product_id=product_id,
            )

            # Перенаправляем к началу оформления заказа
            from aiogram.types import CallbackQuery

            # Создаем фейковый CallbackQuery для использования существующего обработчика
            fake_callback = type('obj', (object,), {
                'data': f'order_start:{product_id}',
                'from_user': message.from_user,
                'message': message,
                'bot': message.bot,
                'answer': lambda text="", show_alert=False: message.answer(text) if text else None,
            })()

            # Вызываем обработчик начала заказа
            from src.bot.handlers.user.order_dialog import start_order
            await start_order(fake_callback, session, state)

            return

        except (ValueError, IndexError) as e:
            logger.error(f"Invalid deep link format: {args}", error=str(e))

    # Если deep link не распознан, показываем обычное приветствие
    await cmd_start(message, user)


@router.message(CommandStart())
async def cmd_start(message: Message, user: User | None = None) -> None:
    """Обработчик команды /start для пользователей.

    Args:
        message: Входящее сообщение
        user: Пользователь из БД
    """
    if not user:
        logger.error("User not found in start handler")
        await message.answer("❌ Ошибка авторизации. Попробуйте позже.")
        return

    logger.info("User started bot", user_id=user.id, telegram_id=user.telegram_id)

    # Приветственное сообщение
    greeting = (
        f"👋 <b>Добро пожаловать, {user.full_name}!</b>\n\n"
        "🛍 <b>Магазин одежды</b>\n\n"
        "Здесь вы можете:\n"
        "📦 Просмотреть каталог товаров\n"
        "🛍 Оформить и отслеживать заказы\n"
        "💬 Получить помощь и поддержку\n\n"
        "Выберите нужный раздел в меню ниже ⬇️"
    )

    await message.answer(
        text=greeting,
        reply_markup=get_user_menu(),
        parse_mode="HTML",
    )
