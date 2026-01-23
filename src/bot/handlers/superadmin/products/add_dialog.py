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

    MEDIA = State()
    NAME = State()
    DESCRIPTION = State()
    PRICE = State()
    SIZES = State()
    COLORS = State()
    FIT = State()
    CATEGORY = State()
    PREVIEW = State()


@router.callback_query(F.data == "prod_add_dialog", IsSuperAdmin())
async def start_add_product(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начать добавление товара."""
    await callback.answer()

    # Инициализируем список медиа
    await state.update_data(media=[])

    text = (
        "➕ <b>Добавление товара</b>\n\n"
        "Шаг 1/8: Отправьте медиа (фото/видео)\n\n"
        "Вы можете отправить до 10 фото или видео.\n"
        "Когда закончите, отправьте команду /done\n\n"
        "Отправьте /cancel для отмены"
    )

    await callback.message.edit_text(text, parse_mode="HTML")
    await state.set_state(AddProductStates.MEDIA)


@router.message(IsSuperAdmin(), AddProductStates.MEDIA, F.photo | F.video)
async def process_media(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка фото или видео."""
    data = await state.get_data()
    media = data.get("media", [])

    if len(media) >= 10:
        await message.answer(
            "❌ Достигнут лимит медиа файлов (10)\n"
            "Отправьте /done для продолжения"
        )
        return

    # Добавляем медиа в список
    if message.photo:
        photo = message.photo[-1]
        media.append({"type": "photo", "file_id": photo.file_id})
    elif message.video:
        media.append({"type": "video", "file_id": message.video.file_id})

    await state.update_data(media=media)

    text = (
        f"✅ Медиа {len(media)}/10 сохранено\n\n"
        f"Отправьте еще медиа или /done для продолжения"
    )

    await message.answer(text, parse_mode="HTML")


@router.message(IsSuperAdmin(), AddProductStates.MEDIA, Command("done"))
async def media_done(
    message: Message,
    state: FSMContext,
) -> None:
    """Завершение добавления медиа."""
    data = await state.get_data()
    media = data.get("media", [])

    if not media:
        await message.answer("❌ Добавьте хотя бы одно фото или видео")
        return

    text = (
        "✅ Медиа сохранены\n\n"
        "Шаг 2/8: Введите название товара\n\n"
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
        "Шаг 3/8: Введите описание товара\n\n"
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
        "Шаг 4/8: Введите цену товара (в рублях)\n\n"
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
        "Шаг 5/8: Введите размеры через запятую\n\n"
        "Например: S, M, L, XL"
    )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(AddProductStates.SIZES)


@router.message(IsSuperAdmin(), AddProductStates.SIZES, F.text)
async def process_sizes(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка размеров."""
    sizes_raw = message.text.strip()
    sizes = [s.strip().upper() for s in sizes_raw.replace(";", ",").split(",") if s.strip()]

    if not sizes:
        await message.answer("❌ Не удалось распознать размеры. Попробуйте еще раз")
        return

    await state.update_data(sizes=sizes)

    text = (
        "✅ Размеры сохранены\n\n"
        "Шаг 6/8: Введите доступные цвета через запятую\n\n"
        "Например: Черный, Белый, Серый\n"
        "Или отправьте - если цветов нет"
    )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(AddProductStates.COLORS)


@router.message(IsSuperAdmin(), AddProductStates.COLORS, F.text)
async def process_colors(
    message: Message,
    state: FSMContext,
) -> None:
    """Обработка цветов."""
    colors_raw = message.text.strip()

    if colors_raw == "-":
        colors = []
    else:
        colors = [c.strip() for c in colors_raw.replace(";", ",").split(",") if c.strip()]

    await state.update_data(colors=colors)

    text = (
        "✅ Цвета сохранены\n\n"
        "Шаг 7/8: Введите тип кроя\n\n"
        "Например: Regular, Slim, Oversize\n"
        "Или отправьте - если не указывается"
    )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(AddProductStates.FIT)


@router.message(IsSuperAdmin(), AddProductStates.FIT, F.text)
async def process_fit(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Обработка типа кроя."""
    fit = message.text.strip() if message.text != "-" else None

    await state.update_data(fit=fit)

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
        "✅ Тип кроя сохранен\n\n"
        "Шаг 8/8: Выберите категорию"
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

        # Для обратной совместимости: если есть media, берем первое фото как photo_file_id
        media = data.get("media", [])
        photo_file_id = None
        if media and media[0]["type"] == "photo":
            photo_file_id = media[0]["file_id"]

        product = await product_service.add_product(
            name=data["name"],
            price=price,
            category_id=category_id,
            sizes=data["sizes"],
            description=data.get("description"),
            photo_file_id=photo_file_id,
            colors=data.get("colors", []),
            fit=data.get("fit"),
            media=media,
        )

        # Формируем текст результата
        text_parts = [
            f"✅ <b>Товар добавлен!</b>\n",
            f"ID: <code>{product.id}</code>",
            f"Название: {product.name}",
            f"Цена: {product.formatted_price}",
            f"Размеры: {', '.join(product.sizes_list)}",
        ]

        if product.colors_list:
            text_parts.append(f"Цвета: {', '.join(product.colors_list)}")

        if product.fit:
            text_parts.append(f"Крой: {product.fit}")

        if product.media_list:
            text_parts.append(f"Медиа: {len(product.media_list)} файл(ов)")

        text_parts.append("\nОпубликовать в канал?")
        text = "\n".join(text_parts)

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
