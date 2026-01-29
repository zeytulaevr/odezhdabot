"""Хендлер команды /start для обычных пользователей."""

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.main_menu import get_user_menu
from src.bot.keyboards.reply import (
    get_admin_keyboard,
    get_superadmin_keyboard,
    remove_keyboard,
)
from src.core.constants import UserRole
from src.core.logging import get_logger
from src.database.models.user import User

logger = get_logger(__name__)

router = Router(name="user_start")


# 🧪 Сообщение о тестовом режиме
TEST_MODE_MESSAGE = (
    "🧪 <b>Бот временно работает в тестовом режиме</b>\n\n"
    "Возможны ошибки или нестабильная работа.\n"
    "Если вы столкнулись с технической проблемой — будем благодарны за обратную связь.\n\n"
    "📞 <b>Контакты магазина в Telegram --</b>\n"
    "<a href=\"https://t.me/Sold_out_ru\">написать в магазин</a>\n\n"
    "👨‍💻 <b>По техническим вопросам:</b>\n"
    "Связаться с разработчиком можно в Telegram —\n"
    "<a href=\"https://t.me/rustyyouth\">написать разработчику</a>"
)


async def send_test_mode_info(message: Message) -> None:
    """Отправляет сообщение о тестовом режиме."""
    await message.answer(
        text=TEST_MODE_MESSAGE,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(
    message: Message,
    command: CommandObject,
    user: User | None = None,
    session: AsyncSession | None = None,
    state: FSMContext | None = None,
) -> None:
    """Обработчик команды /start с deep link."""
    if not user:
        logger.error("User not found in start deep link handler")
        await message.answer("❌ Ошибка авторизации. Попробуйте позже.")
        return

    args = command.args

    # Проверяем, что это именно ссылка на заказ
    if args and args.startswith("order_"):
        try:
            product_id = int(args.split("_")[1])
        except (ValueError, IndexError):
            await cmd_start(message, user)
            return

        logger.info(
            "Deep link order start",
            user_id=user.id,
            product_id=product_id,
        )

        async def fake_answer(text="", show_alert=False, **kwargs):
            if text and show_alert:
                await message.answer(text)
            return True

        fake_callback = type("FakeCallback", (object,), {
            "data": f"order_start:{product_id}",
            "from_user": message.from_user,
            "message": type("FakeMessage", (object,), {
                "photo": None,
                "answer": message.answer,
                "edit_text": message.edit_text,
                "bot": message.bot,
                "delete": message.delete,
            })(),
            "bot": message.bot,
            "answer": fake_answer,
        })()

        from src.bot.handlers.user.order_dialog import start_order

        try:
            await start_order(fake_callback, session, state)

            # 🧪 Сообщение о тестовом режиме (после старта заказа)
            await send_test_mode_info(message)
            return

        except Exception as e:
            logger.error(
                f"Error executing start_order via deep link: {e}",
                exc_info=True,
            )
            await cmd_start(message, user)
            return

    await cmd_start(message, user)


@router.message(CommandStart())
async def cmd_start(message: Message, user: User | None = None) -> None:
    """Обработчик команды /start для пользователей (обычное приветствие)."""
    if not user:
        logger.error("User not found in start handler")
        await message.answer("❌ Ошибка авторизации. Попробуйте позже.")
        return

    logger.info("User started bot", user_id=user.id, role=user.role)

    if user.role == UserRole.SUPER_ADMIN.value:
        reply_keyboard = get_superadmin_keyboard()
        role_info = "👑 <b>Супер-администратор</b>\n\n"
        additional_info = "У вас полный доступ ко всем функциям..."
    elif user.role in [UserRole.ADMIN.value, UserRole.MODERATOR.value]:
        reply_keyboard = get_admin_keyboard()
        role_name = (
            "Администратор"
            if user.role == UserRole.ADMIN.value
            else "Модератор"
        )
        role_info = f"👤 <b>{role_name}</b>\n\n"
        additional_info = "Доступные функции: управление заказами и каталогом."
    else:
        reply_keyboard = remove_keyboard()
        role_info = ""
        additional_info = (
            "Здесь вы можете:\n"
            "📦 Просмотреть каталог товаров\n"
            "🛍 Оформить и отслеживать заказы\n\n"
            "Выберите нужный раздел в меню ниже ⬇️"
        )

    greeting = (
        f"👋 <b>Добро пожаловать, {user.full_name}!</b>\n\n"
        f"{role_info}🛍 <b>Магазин одежды SOLD OUT!</b>\n\n"
        f"{additional_info}"
    )

    await message.answer(
        text=greeting,
        reply_markup=reply_keyboard,
        parse_mode="HTML",
    )

    # 🧪 Сообщение о тестовом режиме
    await send_test_mode_info(message)

    if user.role == UserRole.USER.value:
        await message.answer(
            text="Выберите раздел:",
            reply_markup=get_user_menu(),
            parse_mode="HTML",
        )
