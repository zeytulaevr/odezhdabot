"""Обработчики управления товарами."""

from aiogram import Router

from src.bot.handlers.superadmin.products import add_dialog, manage, upload_file

router = Router(name="products")

router.include_router(add_dialog.router)
router.include_router(manage.router)
router.include_router(upload_file.router)

__all__ = ["router"]
