"""Сервис для отправки уведомлений."""

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from src.core.config import settings
from src.core.logging import get_logger
from src.database.models.order import Order

logger = get_logger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений пользователям и админам."""

    # Эмодзи для статусов
    STATUS_EMOJI = {
        "new": "🆕",
        "processing": "⏳",
        "paid": "💰",
        "shipped": "📦",
        "completed": "✅",
        "cancelled": "❌",
    }

    # Русские названия статусов
    STATUS_NAMES = {
        "new": "Новый",
        "processing": "В обработке",
        "paid": "Оплачен",
        "shipped": "Отправлен",
        "completed": "Выполнен",
        "cancelled": "Отменён",
    }

    @staticmethod
    async def notify_admins_new_order(bot: Bot, order: Order) -> int:
        """Уведомить всех админов о новом заказе.

        Args:
            bot: Telegram Bot instance
            order: Заказ

        Returns:
            Количество успешных уведомлений
        """
        if not settings.superadmin_ids:
            logger.warning("No superadmin IDs configured for notifications")
            return 0

        # Формируем текст уведомления
        product_name = order.product.name if order.product else "Неизвестный товар"
        product_price = order.product.formatted_price if order.product else "—"

        text = (
            f"🆕 <b>Новый заказ #{order.id}</b>\n\n"
            f"👤 Клиент: {order.user.full_name}\n"
            f"📦 Товар: {product_name}\n"
            f"💰 Цена: {product_price}\n"
            f"📏 Размер: {order.size.upper()}\n"
            f"📞 Контакт: {order.customer_contact}\n"
            f"🕐 Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Для обработки заказа используйте команду /admin"
        )

        success_count = 0

        # TODO: В будущем можно отправлять уведомления всем админам из БД
        for admin_id in settings.superadmin_ids:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="HTML",
                )
                success_count += 1
                logger.info(
                    "Admin notified about new order",
                    admin_id=admin_id,
                    order_id=order.id,
                )
            except TelegramBadRequest as e:
                logger.error(
                    "Failed to notify admin",
                    admin_id=admin_id,
                    order_id=order.id,
                    error=str(e),
                )
            except Exception as e:
                logger.error(
                    "Unexpected error notifying admin",
                    admin_id=admin_id,
                    order_id=order.id,
                    error=str(e),
                )

        return success_count

    @staticmethod
    async def notify_user_order_created(bot: Bot, order: Order) -> bool:
        """Уведомить пользователя о создании заказа.

        Args:
            bot: Telegram Bot instance
            order: Заказ

        Returns:
            True при успехе
        """
        product_name = order.product.name if order.product else "Неизвестный товар"
        product_price = order.product.formatted_price if order.product else "—"

        text = (
            f"✅ <b>Ваш заказ принят!</b>\n\n"
            f"📋 Номер заказа: <code>#{order.id}</code>\n"
            f"📦 Товар: {product_name}\n"
            f"💰 Цена: {product_price}\n"
            f"📏 Размер: {order.size.upper()}\n\n"
            f"Мы свяжемся с вами в ближайшее время.\n"
            f"Следите за статусом заказа в разделе 'Мои заказы'."
        )

        try:
            await bot.send_message(
                chat_id=order.user.telegram_id,
                text=text,
                parse_mode="HTML",
            )
            logger.info(
                "User notified about order creation",
                user_id=order.user.id,
                order_id=order.id,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to notify user about order creation",
                user_id=order.user.id,
                order_id=order.id,
                error=str(e),
            )
            return False

    @staticmethod
    async def notify_user_status_change(bot: Bot, order: Order, old_status: str) -> bool:
        """Уведомить пользователя об изменении статуса заказа.

        Args:
            bot: Telegram Bot instance
            order: Заказ
            old_status: Предыдущий статус

        Returns:
            True при успехе
        """
        status_emoji = NotificationService.STATUS_EMOJI.get(order.status, "📋")
        status_name = NotificationService.STATUS_NAMES.get(order.status, order.status)

        old_status_name = NotificationService.STATUS_NAMES.get(old_status, old_status)

        text = (
            f"{status_emoji} <b>Статус заказа изменён</b>\n\n"
            f"📋 Заказ: <code>#{order.id}</code>\n"
            f"📦 Товар: {order.product.name if order.product else 'Неизвестный товар'}\n"
            f"📏 Размер: {order.size.upper()}\n\n"
            f"Старый статус: {old_status_name}\n"
            f"<b>Новый статус: {status_name}</b>\n"
        )

        # Дополнительная информация по статусам
        if order.status == "processing":
            text += "\n⏳ Ваш заказ обрабатывается. Ожидайте подтверждения."
        elif order.status == "paid":
            text += "\n💰 Оплата получена. Готовим к отправке."
        elif order.status == "shipped":
            text += "\n📦 Ваш заказ отправлен. Ожидайте доставку."
        elif order.status == "completed":
            text += "\n✅ Заказ выполнен. Спасибо за покупку!"
        elif order.status == "cancelled":
            text += "\n❌ Заказ отменён."
            if order.admin_notes:
                text += f"\n\nПричина: {order.admin_notes}"

        try:
            await bot.send_message(
                chat_id=order.user.telegram_id,
                text=text,
                parse_mode="HTML",
            )
            logger.info(
                "User notified about status change",
                user_id=order.user.id,
                order_id=order.id,
                old_status=old_status,
                new_status=order.status,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to notify user about status change",
                user_id=order.user.id,
                order_id=order.id,
                error=str(e),
            )
            return False

    @staticmethod
    def get_status_emoji(status: str) -> str:
        """Получить эмодзи для статуса.

        Args:
            status: Статус заказа

        Returns:
            Эмодзи
        """
        return NotificationService.STATUS_EMOJI.get(status, "📋")

    @staticmethod
    def get_status_name(status: str) -> str:
        """Получить русское название статуса.

        Args:
            status: Статус заказа

        Returns:
            Название статуса
        """
        return NotificationService.STATUS_NAMES.get(status, status)
