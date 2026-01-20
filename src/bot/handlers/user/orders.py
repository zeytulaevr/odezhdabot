"""Обработчики заказов для пользователей."""

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.user import User
from src.services.product_service import ProductService

logger = get_logger(__name__)

router = Router(name="orders")


@router.callback_query(F.data.startswith("order:"))
async def callback_order_product(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
) -> None:
    """Обработка заказа товара.

    Args:
        callback: Callback query
        user: Пользователь
        session: Сессия БД
    """
    product_id = int(callback.data.split(":")[1])

    logger.info(
        "Product order initiated",
        product_id=product_id,
        user_id=user.id,
    )

    product_service = ProductService(session)
    product = await product_service.get_product(product_id)

    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    if not product.is_active:
        await callback.answer(
            "❌ Товар больше не доступен для заказа",
            show_alert=True,
        )
        return

    # Формируем сообщение о заказе
    text = (
        f"🛒 <b>Заказ товара</b>\n\n"
        f"📦 Товар: <b>{product.name}</b>\n"
        f"💰 Цена: <b>{product.formatted_price}</b>\n"
        f"📏 Размеры: {', '.join(product.sizes_list)}\n\n"
        f"Для оформления заказа свяжитесь с администратором:\n"
        f"@your_shop_admin\n\n"
        f"Укажите в сообщении:\n"
        f"• Артикул товара: <code>{product.id}</code>\n"
        f"• Желаемый размер\n"
        f"• Способ получения"
    )

    await callback.answer()
    await callback.bot.send_message(
        chat_id=user.telegram_id,
        text=text,
        parse_mode="HTML",
    )

    logger.info(
        "Order information sent to user",
        product_id=product_id,
        user_id=user.id,
    )
