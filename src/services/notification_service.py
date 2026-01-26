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
        "confirmed": "✔️",
        "paid": "💰",
        "shipped": "📦",
        "delivered": "🚚",
        "completed": "✅",
        "cancelled": "❌",
    }

    # Русские названия статусов
    STATUS_NAMES = {
        "new": "Новый",
        "confirmed": "Подтверждён",
        "paid": "Оплачен",
        "shipped": "Отправлен",
        "delivered": "Доставлен",
        "completed": "Завершён",
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

        # Формируем заголовок уведомления
        header = f"🆕 <b>Новый заказ #{order.id}</b>\n\n"
        header += "━━━━━━━━━━━━━━━━━━━━\n"
        header += f"👤 <b>Клиент:</b> {order.user.full_name}\n"
        if order.user.username:
            header += f"📱 <b>Telegram:</b> @{order.user.username}\n"
        header += f"📞 <b>Контакт:</b> {order.customer_contact}\n"
        header += f"🕐 <b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        header += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Формируем информацию о товарах
        items_text = f"🛍️ <b>Товары ({order.total_items} шт.):</b>\n\n"

        for i, item in enumerate(order.items, 1):
            items_text += f"<b>{i}.</b> {item.product_name}\n"
            items_text += f"   📏 Размер: <code>{item.size.upper()}</code>"
            if item.color:
                items_text += f" | 🎨 <i>{item.color}</i>"
            items_text += f"\n   🔢 {item.quantity} шт. × {item.price_at_order:,.2f} ₽ = <b>{item.total_price:,.2f} ₽</b>\n\n"

        footer = "━━━━━━━━━━━━━━━━━━━━\n"
        footer += f"💰 <b>ИТОГО: {order.total_price:,.2f} ₽</b>\n"
        footer += "━━━━━━━━━━━━━━━━━━━━\n\n"
        footer += "⚙️ Для обработки используйте /admin"

        # Объединяем всё
        full_text = header + items_text + footer

        # Проверяем длину сообщения (лимит Telegram - 4096 символов)
        MAX_MESSAGE_LENGTH = 4096

        success_count = 0

        # TODO: В будущем можно отправлять уведомления всем админам из БД
        for admin_id in settings.superadmin_ids:
            try:
                # Если сообщение умещается в один - отправляем как есть
                if len(full_text) <= MAX_MESSAGE_LENGTH:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=full_text,
                        parse_mode="HTML",
                    )
                else:
                    # Иначе разбиваем на части
                    # Первое сообщение - заголовок + краткая информация
                    summary = (
                        header +
                        f"📦 <b>Товаров в заказе: {order.total_items} шт.</b>\n"
                        f"💰 <b>Итого: {order.total_price:,.2f} ₽</b>\n\n"
                        f"⚠️ Детальная информация о товарах отправлена отдельными сообщениями\n\n"
                        f"Для обработки заказа используйте команду /admin"
                    )
                    await bot.send_message(
                        chat_id=admin_id,
                        text=summary,
                        parse_mode="HTML",
                    )

                    # Отправляем товары порциями
                    items_per_message = 5
                    for i in range(0, len(order.items), items_per_message):
                        batch = order.items[i:i + items_per_message]
                        batch_text = f"📦 <b>Товары {i+1}-{i+len(batch)} из {len(order.items)}:</b>\n\n"

                        for j, item in enumerate(batch, start=i+1):
                            batch_text += f"{j}. {item.product_name}\n"
                            batch_text += f"   📏 Размер: {item.size.upper()}\n"
                            if item.color:
                                batch_text += f"   🎨 Цвет: {item.color}\n"
                            batch_text += f"   🔢 Количество: {item.quantity} шт.\n"
                            batch_text += f"   💰 Цена: {item.price_at_order:,.2f} ₽\n"
                            batch_text += f"   💵 Сумма: {item.total_price:,.2f} ₽\n\n"

                        await bot.send_message(
                            chat_id=admin_id,
                            text=batch_text,
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
        # Формируем заголовок
        header = f"✅ <b>Ваш заказ принят!</b>\n\n"
        header += f"📋 Номер заказа: <code>#{order.id}</code>\n"
        header += "━━━━━━━━━━━━━━━━━━━━\n\n"

        # Формируем информацию о товарах
        items_text = f"🛍️ <b>Состав заказа ({order.total_items} шт.):</b>\n\n"

        for i, item in enumerate(order.items, 1):
            items_text += f"<b>{i}.</b> {item.product_name}\n"
            items_text += f"   📏 Размер: <code>{item.size.upper()}</code>"
            if item.color:
                items_text += f" | 🎨 <i>{item.color}</i>"
            items_text += f"\n   🔢 {item.quantity} шт. × {item.price_at_order:,.2f} ₽ = <b>{item.total_price:,.2f} ₽</b>\n\n"

        footer = "━━━━━━━━━━━━━━━━━━━━\n"
        footer += f"💰 <b>ИТОГО: {order.total_price:,.2f} ₽</b>\n"
        footer += "━━━━━━━━━━━━━━━━━━━━\n\n"
        footer += "📞 Мы свяжемся с вами в ближайшее время.\n"
        footer += "📊 Следите за статусом в разделе 'Мои заказы'."

        # Объединяем всё
        full_text = header + items_text + footer

        # Проверяем длину сообщения (лимит Telegram - 4096 символов)
        MAX_MESSAGE_LENGTH = 4096

        try:
            # Если сообщение умещается в один - отправляем как есть
            if len(full_text) <= MAX_MESSAGE_LENGTH:
                await bot.send_message(
                    chat_id=order.user.telegram_id,
                    text=full_text,
                    parse_mode="HTML",
                )
            else:
                # Иначе разбиваем на части
                # Первое сообщение - заголовок + краткая информация
                summary = (
                    header +
                    f"📦 <b>Товаров в заказе: {order.total_items} шт.</b>\n"
                    f"💰 <b>Итого: {order.total_price:,.2f} ₽</b>\n\n"
                    f"⚠️ Детальная информация о товарах отправлена отдельными сообщениями\n\n"
                    f"Мы свяжемся с вами в ближайшее время.\n"
                    f"Следите за статусом заказа в разделе 'Мои заказы'."
                )
                await bot.send_message(
                    chat_id=order.user.telegram_id,
                    text=summary,
                    parse_mode="HTML",
                )

                # Отправляем товары порциями
                items_per_message = 5
                for i in range(0, len(order.items), items_per_message):
                    batch = order.items[i:i + items_per_message]
                    batch_text = f"📦 <b>Товары {i+1}-{i+len(batch)} из {len(order.items)}:</b>\n\n"

                    for j, item in enumerate(batch, start=i+1):
                        batch_text += f"{j}. {item.product_name}\n"
                        batch_text += f"   📏 Размер: {item.size.upper()}\n"
                        if item.color:
                            batch_text += f"   🎨 Цвет: {item.color}\n"
                        batch_text += f"   🔢 Количество: {item.quantity} шт.\n"
                        batch_text += f"   💰 Цена: {item.price_at_order:,.2f} ₽\n"
                        batch_text += f"   💵 Сумма: {item.total_price:,.2f} ₽\n\n"

                    await bot.send_message(
                        chat_id=order.user.telegram_id,
                        text=batch_text,
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
            f"📦 Товаров: {order.total_items} шт.\n"
            f"💰 Сумма: {order.total_price:,.2f} ₽\n\n"
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
