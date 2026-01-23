"""Хендлеры для администраторов."""

from aiogram import Router

from src.bot.handlers.admin import menu, moderation_queue, order_actions, orders, users

# Главный роутер для админов
router = Router(name="admin")

# Подключаем суб-роутеры
router.include_router(order_actions.router)  # Действия с заказами (FSM)
router.include_router(orders.router)  # Просмотр заказов
router.include_router(users.router)  # Управление пользователями
router.include_router(menu.router)
router.include_router(moderation_queue.router)

__all__ = ["router"]
