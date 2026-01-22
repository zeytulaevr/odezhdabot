"""Обработчики для системы массовых рассылок."""

from aiogram import Router

from src.bot.handlers.superadmin.broadcast import create, history

# Главный роутер для рассылок
router = Router(name="broadcast")

# Подключаем суб-роутеры
# FSM обработчики должны быть первыми
router.include_router(create.router)
router.include_router(history.router)

__all__ = ["router"]
