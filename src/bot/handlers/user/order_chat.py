"""Обработчики чата с администратором по заказу."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.order import Order
from src.database.models.order_message import OrderMessage
from src.database.models.user import User, UserRole

logger = get_logger(__name__)

router = Router(name="user_order_chat")


@router.message(F.reply_to_message, F.text)
async def handle_reply_to_order_message(
    message: Message,
    session: AsyncSession,
    user: User,
) -> None:
    """Обработать ответ на сообщение по заказу.

    Если пользователь отвечает на сообщение от администратора,
    его ответ сохраняется в базу и пересылается админу.

    Args:
        message: Message с ответом
        session: Сессия БД
        user: Пользователь
    """
    # Проверяем, что это ответ на сообщение от бота
    if not message.reply_to_message or not message.reply_to_message.from_user.is_bot:
        return

    # Ищем в тексте сообщения номер заказа (формат "заказ #123" или "#123")
    import re

    replied_text = message.reply_to_message.text or message.reply_to_message.caption or ""
    order_pattern = r"заказ.*?#(\d+)|#(\d+)"
    match = re.search(order_pattern, replied_text, re.IGNORECASE)

    if not match:
        # Не нашли номер заказа - возможно это не сообщение о заказе
        return

    order_id = int(match.group(1) or match.group(2))

    # Получаем заказ
    result = await session.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        await message.answer("❌ Заказ не найден")
        return

    # Проверяем, что это заказ пользователя или он админ
    is_admin = user.role in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]

    if not is_admin and order.user_id != user.id:
        await message.answer("❌ Это не ваш заказ")
        return

    # Сохраняем сообщение в БД
    order_message = OrderMessage(
        order_id=order_id,
        sender_id=user.id,
        message_text=message.text,
        is_read=False,
    )

    session.add(order_message)
    await session.flush()
    await session.commit()

    # Определяем, кому пересылать сообщение
    if is_admin:
        # Админ пишет клиенту
        recipient_id = order.user.telegram_id
        notification_text = (
            f"💬 <b>Новое сообщение по заказу #{order_id}</b>\n\n"
            f"{message.text}\n\n"
            f"<i>Ответьте на это сообщение, чтобы написать администратору.</i>"
        )
    else:
        # Клиент пишет админу - отправляем всем админам
        from src.core.config import settings

        notification_text = (
            f"💬 <b>Сообщение от клиента по заказу #{order_id}</b>\n\n"
            f"👤 {user.full_name}"
        )
        if user.username:
            notification_text += f" (@{user.username})"
        notification_text += f"\n\n{message.text}\n\n"
        notification_text += f"<i>Для ответа используйте: /admin → Заказы → #{order_id} → Написать клиенту</i>"

        # Отправляем уведомление всем админам
        if settings.superadmin_ids:
            for admin_id in settings.superadmin_ids:
                try:
                    await message.bot.send_message(
                        chat_id=admin_id,
                        text=notification_text,
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(
                        "Failed to notify admin about client message",
                        admin_id=admin_id,
                        order_id=order_id,
                        error=str(e),
                    )

        await message.answer("✅ Сообщение отправлено администратору")
        logger.info(
            "Client message sent to admin",
            user_id=user.id,
            order_id=order_id,
        )
        return

    # Отправляем уведомление получателю (если админ пишет клиенту)
    try:
        await message.bot.send_message(
            chat_id=recipient_id,
            text=notification_text,
            parse_mode="HTML",
        )
        await message.answer("✅ Сообщение отправлено")
        logger.info(
            "Admin message sent to client",
            admin_id=user.id,
            order_id=order_id,
            client_id=order.user.id,
        )
    except Exception as e:
        logger.error(
            "Failed to send message",
            order_id=order_id,
            error=str(e),
        )
        await message.answer("❌ Не удалось отправить сообщение")
