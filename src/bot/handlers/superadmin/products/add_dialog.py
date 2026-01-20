"""FSM диалог добавления товара."""

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.products import get_categories_keyboard
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.category import CategoryRepository
from src.services.product_service import ProductService

logger = get_logger(__name__)

router = Router(name="product_add_dialog")


class AddProductStates(StatesGroup):
    """Состояния добавления товара."""

    PHOTO = State()
    NAME = State()
    DESCRIPTION = State()
    PRICE = State()
    SIZES = State()
    CATEGORY = State()
    PREVIEW = State()


@router.callback_query(F.data == "prod_add_dialog", IsSuperAdmin())
async def start_add_product(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать добавление товара."""
    await callback.answer()

    text = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 1/5: Отправьте фото товара\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(AddProductStates.PHOTO)


@router.message(IsSuperAdmin(), AddProductStates.PHOTO, F.photo)
async def process_photo(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка фото."""
    # Берем самое большое фото
    photo = message.photo[-1]

    await state.update_data(photo_file_id=photo.file_id)

    text = (
        "✅ Фото сохранено\n\n"
        "Шаг 2/5: Введите название товара\n\n"
        "Например: Футболка Oversize"
    )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(AddProductStates.NAME)


@router.message(IsSuperAdmin(), AddProductStates.NAME, F.text)
async def process_name(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка названия."""
    name = message.text.strip()

    if len(name) < 3:
        await message.answer("❌ Название слишком короткое (минимум 3 символа)")
        return

    await state.update_data(name=name)

    text = (
        "✅ Название сохранено\n\n"
        "Шаг 3/5: Введите описание товара\n\n"
        "Или отправьте - если описание не нужно"
    )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(AddProductStates.DESCRIPTION)


@router.message(IsSuperAdmin(), AddProductStates.DESCRIPTION, F.text)
async def process_description(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка описания."""
    description = message.text.strip() if message.text != "-" else None

    await state.update_data(description=description)

    text = (
        "✅ Описание сохранено\n\n"
        "Шаг 4/5: Введите цену товара (в рублях)\n\n"
        "Например: 1999 или 1999.99"
    )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(AddProductStates.PRICE)


@router.message(IsSuperAdmin(), AddProductStates.PRICE, F.text)
async def process_price(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка цены."""
    try:
        price_str = message.text.strip().replace(",", ".").replace(" ", "")
        price = Decimal(price_str)

        if price <= 0:
            await message.answer("❌ Цена должна быть больше 0")
            return

    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ Некорректная цена. Введите число (например: 1999 или 1999.99)"
        )
        return

    # Store as string for JSON serialization in Redis
    await state.update_data(price=str(price))

    text = (
        "✅ Цена сохранена\n\n"
        "Шаг 5/5: Введите размеры через запятую\n\n"
        "Например: S, M, L, XL"
    )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(AddProductStates.SIZES)


@router.message(IsSuperAdmin(), AddProductStates.SIZES, F.text)
async def process_sizes(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обработка размеров."""
    sizes_raw = message.text.strip()
    sizes = [s.strip().upper() for s in sizes_raw.replace(";", ",").split(",") if s.strip()]

    if not sizes:
        await message.answer("❌ Не удалось распознать размеры. Попробуйте еще раз")
        return

    await state.update_data(sizes=sizes)

    # Показываем категории
    category_repo = CategoryRepository(session)
    categories = await category_repo.get_all()

    if not categories:
        await message.answer(
            "❌ Нет категорий. Сначала создайте категорию через /categories"
        )
        await state.clear()
        return

    text = (
        "✅ Размеры сохранены\n\n"
        "Шаг 6/6: Выберите категорию"
    )

    keyboard = get_categories_keyboard(categories)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AddProductStates.CATEGORY)


@router.callback_query(IsSuperAdmin(), AddProductStates.CATEGORY, F.data.startswith("cat:"))
async def process_category(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Обработка выбора категории и сохранение товара."""
    category_id = int(callback.data.split(":")[1])

    await callback.answer()

    # Получаем все данные
    data = await state.get_data()

    # Создаем товар
    product_service = ProductService(session)

    try:
        # Convert price string back to Decimal
        price = Decimal(data["price"])

        product = await product_service.add_product(
            name=data["name"],
            price=price,
            category_id=category_id,
            sizes=data["sizes"],
            description=data.get("description"),
            photo_file_id=data["photo_file_id"],
        )

        text = (
            f"✅ <b>Товар добавлен!</b>\n\n"
            f"ID: <code>{product.id}</code>\n"
            f"Название: {product.name}\n"
            f"Цена: {product.formatted_price}\n"
            f"Размеры: {', '.join(product.sizes_list)}\n\n"
            f"Опубликовать в канал?"
        )

        from src.bot.keyboards.products import get_product_actions_keyboard

        await callback.message.edit_text(
            text,
            reply_markup=get_product_actions_keyboard(product.id),
            parse_mode="HTML",
        )

        await state.clear()

        logger.info(
            "Product added via dialog",
            product_id=product.id,
            admin_id=user.id,
        )

    except Exception as e:
        logger.error(f"Failed to create product: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Ошибка при создании товара:\n<code>{str(e)}</code>",
            parse_mode="HTML",
        )
        await state.clear()


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """Отмена добавления."""
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("❌ Добавление товара отменено")
