"""Репозиторий для работы с отзывами."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.review import Review
from src.database.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    """Репозиторий для работы с отзывами на товары."""

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория отзывов."""
        super().__init__(Review, session)

    async def get_pending_reviews(self, limit: int = 50) -> list[Review]:
        """Получить отзывы на модерации.

        Args:
            limit: Максимальное количество отзывов

        Returns:
            Список отзывов ожидающих модерации
        """
        stmt = (
            select(Review)
            .where(Review.moderation_status == "pending")
            .order_by(Review.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_approved_reviews(
        self, product_id: int | None = None, limit: int = 100
    ) -> list[Review]:
        """Получить одобренные отзывы.

        Args:
            product_id: ID товара (опционально)
            limit: Максимальное количество отзывов

        Returns:
            Список одобренных отзывов
        """
        stmt = select(Review).where(
            Review.is_approved == True,
            Review.moderation_status == "approved"
        )

        if product_id is not None:
            stmt = stmt.where(Review.product_id == product_id)

        stmt = stmt.order_by(Review.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def approve_review(self, review_id: int) -> Review | None:
        """Одобрить отзыв.

        Args:
            review_id: ID отзыва

        Returns:
            Обновлённый отзыв или None
        """
        return await self.update(
            review_id,
            is_approved=True,
            moderation_status="approved"
        )

    async def reject_review(self, review_id: int) -> Review | None:
        """Отклонить отзыв.

        Args:
            review_id: ID отзыва

        Returns:
            Обновлённый отзыв или None
        """
        return await self.update(
            review_id,
            is_approved=False,
            moderation_status="rejected"
        )

    async def flag_review(self, review_id: int) -> Review | None:
        """Отметить отзыв как подозрительный.

        Args:
            review_id: ID отзыва

        Returns:
            Обновлённый отзыв или None
        """
        return await self.update(review_id, moderation_status="flagged")
