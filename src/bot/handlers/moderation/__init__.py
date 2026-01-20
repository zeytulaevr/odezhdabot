"""Обработчики модерации."""

from aiogram import Router

from src.bot.handlers.moderation import channel_monitor

# Создаём главный роутер для модерации
router = Router(name="moderation")

# Подключаем суб-роутеры
router.include_router(channel_monitor.router)

__all__ = ["router"]
