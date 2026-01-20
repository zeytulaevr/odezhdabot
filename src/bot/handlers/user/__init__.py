"""Хендлеры для пользователей."""

from aiogram import Router

from src.bot.handlers.user import orders, start

# Главный роутер для пользователей
router = Router(name="user")

# Подключаем суб-роутеры
router.include_router(start.router)
router.include_router(orders.router)

__all__ = ["router"]
