#!/usr/bin/env python3
"""Скрипт для обновления ролей администраторов из ADMIN_IDS."""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import select

from src.core.config import settings
from src.core.constants import UserRole
from src.core.logging import get_logger, setup_logging
from src.database.base import close_db, init_db
from src.database.models.user import User
from src.database.repositories.user import UserRepository

setup_logging()
logger = get_logger(__name__)


async def update_admin_roles() -> None:
    """Обновить роли пользователей из ADMIN_IDS на super_admin."""
    logger.info("Starting admin roles update...")
    logger.info(f"Admin IDs from config: {settings.admin_ids}")

    # Инициализация БД
    await init_db()

    # Получаем сессию напрямую из SessionLocal
    from src.database.base import SessionLocal

    async with SessionLocal() as session:
        user_repo = UserRepository(session)

        # Обновляем роли для всех пользователей из ADMIN_IDS
        updated_count = 0
        for admin_id in settings.admin_ids:
            user = await user_repo.get_by_telegram_id(admin_id)

            if user:
                if user.role != UserRole.SUPER_ADMIN.value:
                    user.role = UserRole.SUPER_ADMIN.value
                    await session.commit()
                    await session.refresh(user)
                    logger.info(
                        f"✅ Updated user role to super_admin",
                        telegram_id=admin_id,
                        user_id=user.id,
                        username=user.username,
                    )
                    updated_count += 1
                else:
                    logger.info(
                        f"ℹ️  User already has super_admin role",
                        telegram_id=admin_id,
                        user_id=user.id,
                        username=user.username,
                    )
            else:
                logger.warning(
                    f"⚠️  User not found in database. User will get super_admin role on first message.",
                    telegram_id=admin_id,
                )

    await close_db()

    logger.info(f"✅ Admin roles update completed. Updated {updated_count} users.")
    print(f"\n✅ Обновлено ролей: {updated_count}")
    print(f"📋 Всего админов в конфиге: {len(settings.admin_ids)}")


if __name__ == "__main__":
    try:
        asyncio.run(update_admin_roles())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Script failed", error=str(e), exc_info=True)
        sys.exit(1)
