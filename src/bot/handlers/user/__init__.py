"""Хендлеры для пользователей."""

from aiogram import Router

from src.bot.handlers.user import catalog, my_orders, order_dialog, start

# Главный роутер для пользователей
router = Router(name="user")

# Подключаем суб-роутеры в порядке приоритета
router.include_router(start.router)  # /start (включая deep link)
router.include_router(order_dialog.router)  # FSM диалог заказа
router.include_router(catalog.router)  # Каталог товаров
router.include_router(my_orders.router)  # Мои заказы

__all__ = ["router"]
