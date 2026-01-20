"""Управление товарами: просмотр, редактирование, удаление."""

import math

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.role import IsSuperAdmin
from src.bot.keyboards.products import (
    get_confirm_delete_keyboard,
    get_product_actions_keyboard,
    get_products_list_keyboard,
    get_products_menu_keyboard,
)
from src.core.config import settings
from src.core.logging import get_logger
from src.database.models.user import User
from src.services.product_service import ProductService

logger = get_logger(__name__)

router = Router(name="product_manage")

PRODUCTS_PER_PAGE = 10


@router.message(Command("products"), IsSuperAdmin())
@router.callback_query(F.data == "products_menu", IsSuperAdmin())
async def products_menu(
    event: Message | CallbackQuery,
    user: User,
) -> None:
    """Главное меню управления товарами."""
    text = (
        "🛍 <b>Управление товарами</b>\n\n"
        "Выберите действие:"
    )

    keyboard = get_products_menu_keyboard()

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "products_list", IsSuperAdmin())
@router.callback_query(F.data.startswith("prod_page:"), IsSuperAdmin())
async def products_list(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Список всех товаров."""
    # Получаем номер страницы
    if callback.data.startswith("prod_page:"):
        page = int(callback.data.split(":")[1])
    else:
        page = 0

    await callback.answer()

    product_service = ProductService(session)

    # Получаем общее количество
    total_count = await product_service.get_products_count()
    total_pages = math.ceil(total_count / PRODUCTS_PER_PAGE) or 1

    # Получаем товары для текущей страницы
    products = await product_service.get_products(
        skip=page * PRODUCTS_PER_PAGE,
        limit=PRODUCTS_PER_PAGE,
    )

    if not products:
        text = "📭 Нет товаров"
        keyboard = get_products_menu_keyboard()
    else:
        text = (
            f"📋 <b>Список товаров</b>\n\n"
            f"Всего: {total_count}\n"
            f"Страница {page + 1} из {total_pages}"
        )
        keyboard = get_products_list_keyboard(products, page, total_pages)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("prod_view:"), IsSuperAdmin())
async def view_product(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Просмотр товара."""
    product_id = int(callback.data.split(":")[1])

    await callback.answer()

    product_service = ProductService(session)
    product = await product_service.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    status = "✅ Активен" if product.is_active else "❌ Неактивен"

    text = (
        f"🛍 <b>{product.name}</b>\n\n"
        f"ID: <code>{product.id}</code>\n"
        f"Статус: {status}\n"
        f"Категория: {product.category.name}\n"
        f"Цена: <b>{product.formatted_price}</b>\n"
        f"Размеры: {', '.join(product.sizes_list)}\n\n"
    )

    if product.description:
        text += f"<b>Описание:</b>\n{product.description}\n\n"

    if product.photo_file_id:
        keyboard = get_product_actions_keyboard(product.id, product.is_active)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=product.photo_file_id,
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    else:
        keyboard = get_product_actions_keyboard(product.id, product.is_active)
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("prod_publish:"), IsSuperAdmin())
async def publish_product(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Опубликовать товар в канал."""
    product_id = int(callback.data.split(":")[1])

    await callback.answer("⏳ Публикация...")

    product_service = ProductService(session)

    try:
        # TODO: получить channel_id из конфига
        channel_id = settings.admin_ids[0]  # Временно
        message_id = await product_service.publish_to_channel(
            product_id, callback.bot, channel_id
        )

        await callback.answer(f"✅ Опубликовано (ID: {message_id})", show_alert=True)

    except Exception as e:
        logger.error(f"Failed to publish product: {e}")
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("prod_activate:"), IsSuperAdmin())
async def activate_product(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Активировать товар."""
    product_id = int(callback.data.split(":")[1])

    product_service = ProductService(session)
    await product_service.activate_product(product_id)

    await callback.answer("✅ Товар активирован")
    await view_product(callback, session)


@router.callback_query(F.data.startswith("prod_deactivate:"), IsSuperAdmin())
async def deactivate_product(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Деактивировать товар."""
    product_id = int(callback.data.split(":")[1])

    product_service = ProductService(session)
    await product_service.deactivate_product(product_id)

    await callback.answer("✅ Товар деактивирован")
    await view_product(callback, session)


@router.callback_query(F.data.startswith("prod_delete:"), IsSuperAdmin())
async def delete_product_confirm(
    callback: CallbackQuery,
) -> None:
    """Подтверждение удаления."""
    product_id = int(callback.data.split(":")[1])

    await callback.answer()

    text = "⚠️ <b>Удаление товара</b>\n\nВы уверены?"

    keyboard = get_confirm_delete_keyboard(product_id)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("prod_delete_confirm:"), IsSuperAdmin())
async def delete_product(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Удалить товар."""
    product_id = int(callback.data.split(":")[1])

    product_service = ProductService(session)
    success = await product_service.delete_product(product_id, soft=True)

    if success:
        await callback.answer("✅ Товар удалён", show_alert=True)
        await products_list(callback, session)
    else:
        await callback.answer("❌ Ошибка удаления", show_alert=True)
