"""Обработчики каталога товаров для пользователей."""

import math

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.main_menu import (
    get_admin_menu,
    get_superadmin_menu,
    get_user_menu,
)
from src.bot.keyboards.orders import get_size_selection_keyboard
from src.core.constants import UserRole
from src.core.logging import get_logger
from src.database.models.user import User
from src.database.repositories.category import CategoryRepository
from src.services.product_service import ProductService
from src.utils.navigation import edit_message_with_navigation, NavigationStack

logger = get_logger(__name__)

router = Router(name="user_catalog")

PRODUCTS_PER_PAGE = 5  # Товаров на странице


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery) -> None:
    """Обработчик для неинтерактивных кнопок (счетчики и т.п.)."""
    await callback.answer()


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    """Вернуться в главное меню."""
    await NavigationStack.clear(state)

    # Определяем меню в зависимости от роли пользователя
    if user.role == UserRole.SUPER_ADMIN:
        menu_markup = get_superadmin_menu()
        menu_title = "👑 Супер-админ панель"
    elif user.role == UserRole.ADMIN:
        menu_markup = get_admin_menu()
        menu_title = "👨‍💼 Админ-панель"
    else:
        menu_markup = get_user_menu()
        menu_title = "🏠 Главное меню"

    text = (
        f"{menu_title}\n\n"
        "Выберите действие:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=menu_markup,
        parse_mode="HTML",
    )
    await callback.answer()


async def build_catalog_keyboard(categories: list):
    """Построить клавиатуру каталога с категориями."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    for category in categories:
        builder.row(
            InlineKeyboardButton(
                text=f"📁 {category.name}",
                callback_data=f"catalog_category:{category.id}",
            )
        )

    builder.row(
        InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_menu")
    )

    return builder.as_markup()


async def build_product_detail_keyboard(
    product_id: int,
    category_id: int,
    current_index: int,
    total_products: int,
):
    """Построить клавиатуру для просмотра товара."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()

    # Кнопка заказа
    builder.row(
        InlineKeyboardButton(
            text="🛒 Заказать",
            callback_data=f"order_start:{product_id}",
        )
    )

    # Навигация между товарами
    nav_buttons = []

    if current_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Предыдущий",
                callback_data=f"catalog_product:{category_id}:{current_index - 1}",
            )
        )

    # Счетчик товаров
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{current_index + 1}/{total_products}",
            callback_data="noop",
        )
    )

    if current_index < total_products - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Следующий ➡️",
                callback_data=f"catalog_product:{category_id}:{current_index + 1}",
            )
        )

    if nav_buttons:
        builder.row(*nav_buttons)

    # Кнопка назад к списку категорий
    builder.row(
        InlineKeyboardButton(
            text="◀️ К категориям",
            callback_data="catalog",
        )
    )

    return builder.as_markup()


@router.callback_query(F.data == "catalog")
@router.message(F.text == "📦 Каталог")
async def show_catalog(
    event: Message | CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать каталог - список категорий.

    Args:
        event: Message или CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    category_repo = CategoryRepository(session)
    categories = await category_repo.get_active_categories()

    if not categories:
        text = (
            "📭 <b>Каталог пуст</b>\n\n"
            "К сожалению, сейчас нет доступных товаров.\n"
            "Загляните позже!"
        )
        keyboard = None
    else:
        text = (
            "📦 <b>Каталог товаров</b>\n\n"
            "Выберите категорию для просмотра товаров:"
        )
        keyboard = await build_catalog_keyboard(categories)

    # Очищаем историю навигации при входе в каталог
    await NavigationStack.clear(state)

    if isinstance(event, CallbackQuery):
        await edit_message_with_navigation(
            callback=event,
            state=state,
            text=text,
            markup=keyboard,
            save_to_history=False,  # Не сохраняем главную страницу каталога
        )
    else:
        await event.answer(
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    logger.info(
        "Catalog opened",
        user_id=event.from_user.id,
        categories_count=len(categories),
    )


@router.callback_query(F.data.startswith("catalog_category:"))
async def show_category_products(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать первый товар из категории.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    category_id = int(callback.data.split(":")[1])

    category_repo = CategoryRepository(session)
    category = await category_repo.get(category_id)

    if not category:
        await callback.answer("❌ Категория не найдена", show_alert=True)
        return

    # Получаем товары категории
    product_service = ProductService(session)
    products = await product_service.get_products(
        category_id=category_id,
        is_active=True,
    )

    if not products:
        text = (
            f"📭 <b>{category.name}</b>\n\n"
            "В этой категории пока нет товаров."
        )

        keyboard_builder = __import__('aiogram.utils.keyboard', fromlist=['InlineKeyboardBuilder']).InlineKeyboardBuilder()
        keyboard_builder.row(
            __import__('aiogram.types', fromlist=['InlineKeyboardButton']).InlineKeyboardButton(
                text="◀️ К категориям",
                callback_data="catalog",
            )
        )
        keyboard = keyboard_builder.as_markup()

        await edit_message_with_navigation(
            callback=callback,
            state=state,
            text=text,
            markup=keyboard,
        )
        return

    # Показываем первый товар
    callback.data = f"catalog_product:{category_id}:0"
    await show_product_detail(callback, session, state)


@router.callback_query(F.data.startswith("catalog_product:"))
async def show_product_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Показать детали товара с фото.

    Args:
        callback: CallbackQuery
        session: Сессия БД
        state: FSM контекст
    """
    parts = callback.data.split(":")
    category_id = int(parts[1])
    product_index = int(parts[2])

    # Получаем товары категории
    product_service = ProductService(session)
    products = await product_service.get_products(
        category_id=category_id,
        is_active=True,
    )

    if not products or product_index >= len(products):
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    product = products[product_index]

    # Формируем красивое описание товара
    text = (
        f"<b>{product.name}</b>\n\n"
        f"💰 Цена: <b>{product.formatted_price}</b>\n"
    )

    if product.sizes_list:
        text += f"📏 Размеры: {', '.join(product.sizes_list)}\n"

    if product.description:
        text += f"\n📝 {product.description}\n"

    text += f"\n📁 Категория: {product.category.name if product.category else '—'}"

    # Клавиатура с навигацией
    keyboard = await build_product_detail_keyboard(
        product_id=product.id,
        category_id=category_id,
        current_index=product_index,
        total_products=len(products),
    )

    # Если есть фото, отправляем/обновляем с фото
    if product.photo_file_id:
        # Сохраняем в историю навигации
        await NavigationStack.push(
            state=state,
            text=text,
            markup=keyboard,
            photo_file_id=product.photo_file_id,
            callback_data=callback.data,
            product_id=product.id,
        )

        try:
            # Пробуем отредактировать медиа
            await callback.message.edit_media(
                media=__import__('aiogram.types', fromlist=['InputMediaPhoto']).InputMediaPhoto(
                    media=product.photo_file_id,
                    caption=text,
                    parse_mode="HTML",
                ),
                reply_markup=keyboard,
            )
            await callback.answer()
        except:
            # Если не получилось отредактировать, удаляем и отправляем новое
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=product.photo_file_id,
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            await callback.answer()
    else:
        # Без фото - обычное текстовое сообщение
        await edit_message_with_navigation(
            callback=callback,
            state=state,
            text=text,
            markup=keyboard,
        )

    logger.info(
        "Product viewed",
        user_id=callback.from_user.id,
        product_id=product.id,
        product_index=product_index,
    )
