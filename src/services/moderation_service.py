"""Сервис модерации сообщений."""

import json
import re
from datetime import datetime
from typing import NamedTuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.models.moderated_message import ModeratedMessage
from src.database.models.spam_pattern import SpamPattern
from src.database.repositories.moderated_message import ModeratedMessageRepository
from src.database.repositories.spam_pattern import SpamPatternRepository
from src.utils.text_analyzer import TextAnalyzer, calculate_text_similarity

logger = get_logger(__name__)


class ModerationDecision(NamedTuple):
    """Решение модерации."""

    should_delete: bool  # Удалять ли сообщение
    should_notify_admins: bool  # Уведомлять ли админов
    spam_score: int  # Оценка спама 0-100
    reasons: list[str]  # Причины
    status: str  # Статус: auto_approved, auto_rejected, pending


class ModerationService:
    """Сервис для модерации сообщений."""

    # Пороги для принятия решений
    HIGH_SPAM_THRESHOLD = 90  # Автоматическое удаление
    SUSPICIOUS_THRESHOLD = 50  # Отправка на ручную проверку

    def __init__(self, session: AsyncSession):
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy сессия
        """
        self.session = session
        self.moderated_msg_repo = ModeratedMessageRepository(session)
        self.spam_pattern_repo = SpamPatternRepository(session)
        self._patterns_cache: list[SpamPattern] | None = None

    async def _get_patterns(self) -> list[SpamPattern]:
        """Получить активные паттерны (с кешированием).

        Returns:
            Список активных паттернов
        """
        if self._patterns_cache is None:
            self._patterns_cache = await self.spam_pattern_repo.get_active_patterns()
            logger.info(f"Loaded {len(self._patterns_cache)} spam patterns")
        return self._patterns_cache

    def invalidate_patterns_cache(self) -> None:
        """Сбросить кеш паттернов."""
        self._patterns_cache = None

    async def check_spam_patterns(self, text: str) -> tuple[int, list[str]]:
        """Проверить текст по паттернам из БД.

        Args:
            text: Текст для проверки

        Returns:
            Кортеж (score, matched_patterns)
        """
        patterns = await self._get_patterns()
        score = 0
        matched = []

        for pattern in patterns:
            try:
                if pattern.is_keyword:
                    # Поиск ключевого слова (case-insensitive)
                    if pattern.pattern.lower() in text.lower():
                        score += 20
                        matched.append(f"keyword:{pattern.pattern}")

                elif pattern.is_regex:
                    # Поиск по regex
                    if re.search(pattern.pattern, text, re.IGNORECASE):
                        score += 25
                        matched.append(f"regex:{pattern.pattern[:30]}")

                elif pattern.is_url:
                    # Проверка URL паттернов
                    urls = TextAnalyzer.extract_urls(text)
                    for url in urls:
                        if pattern.pattern in url:
                            score += 30
                            matched.append(f"url:{pattern.pattern}")

            except re.error as e:
                logger.warning(f"Invalid regex pattern {pattern.id}: {e}")
                continue

        return min(score, 100), matched

    async def check_repeated_content(
        self, user_id: int, text: str, hours: int = 24
    ) -> tuple[int, list[str]]:
        """Проверить на повторяющийся контент.

        Args:
            user_id: ID пользователя
            text: Текст сообщения
            hours: За сколько часов проверять

        Returns:
            Кортеж (score, reasons)
        """
        recent_messages = await self.moderated_msg_repo.get_user_recent_messages(
            user_id, hours=hours, limit=10
        )

        if not recent_messages:
            return 0, []

        max_similarity = 0.0
        similar_count = 0

        for msg in recent_messages:
            similarity = calculate_text_similarity(text, msg.text)
            if similarity > 0.7:
                similar_count += 1
                max_similarity = max(max_similarity, similarity)

        if similar_count > 0:
            score = min(similar_count * 15, 50)
            reasons = [
                f"Похожие сообщения: {similar_count} за {hours}ч "
                f"(сходство {int(max_similarity * 100)}%)"
            ]
            return score, reasons

        return 0, []

    async def moderate_message(
        self,
        message_id: int,
        chat_id: int,
        user_id: int | None,
        text: str,
        thread_id: int | None = None,
    ) -> ModerationDecision:
        """Провести модерацию сообщения.

        Args:
            message_id: Telegram ID сообщения
            chat_id: Telegram ID чата
            user_id: ID пользователя в БД
            text: Текст сообщения
            thread_id: ID ветки

        Returns:
            Решение модерации
        """
        logger.info(
            "Moderating message",
            message_id=message_id,
            chat_id=chat_id,
            user_id=user_id,
        )

        # Базовый анализ текста
        analysis = TextAnalyzer.analyze(text)
        total_score = analysis.spam_score
        all_reasons = list(analysis.reasons)

        # Проверка по паттернам из БД
        pattern_score, matched_patterns = await self.check_spam_patterns(text)
        total_score += pattern_score
        all_reasons.extend(matched_patterns)

        # Проверка повторяющегося контента
        if user_id:
            repeat_score, repeat_reasons = await self.check_repeated_content(
                user_id, text
            )
            total_score += repeat_score
            all_reasons.extend(repeat_reasons)

        # Ограничиваем максимум
        total_score = min(total_score, 100)

        # Принятие решения
        if total_score >= self.HIGH_SPAM_THRESHOLD:
            status = "auto_rejected"
            should_delete = True
            should_notify = True
        elif total_score >= self.SUSPICIOUS_THRESHOLD:
            status = "pending"
            should_delete = False
            should_notify = True
        else:
            status = "auto_approved"
            should_delete = False
            should_notify = False

        # Сохраняем в БД
        try:
            await self.moderated_msg_repo.create(
                user_id=user_id,
                message_id=message_id,
                chat_id=chat_id,
                thread_id=thread_id,
                text=text,
                status=status,
                spam_score=total_score,
                spam_reasons=json.dumps(all_reasons, ensure_ascii=False),
                is_deleted=should_delete,
            )
            await self.session.commit()
        except Exception as e:
            logger.error("Failed to save moderation result", error=str(e))
            await self.session.rollback()

        logger.info(
            "Moderation decision",
            message_id=message_id,
            spam_score=total_score,
            status=status,
            should_delete=should_delete,
        )

        return ModerationDecision(
            should_delete=should_delete,
            should_notify_admins=should_notify,
            spam_score=total_score,
            reasons=all_reasons,
            status=status,
        )

    async def approve_message_by_admin(
        self, moderated_message_id: int, moderator_id: int, comment: str | None = None
    ) -> bool:
        """Одобрить сообщение админом.

        Args:
            moderated_message_id: ID записи модерации
            moderator_id: ID модератора
            comment: Комментарий

        Returns:
            Успешно ли одобрено
        """
        result = await self.moderated_msg_repo.approve_message(
            moderated_message_id, moderator_id, comment
        )
        if result:
            await self.session.commit()
            logger.info(
                "Message approved by admin",
                message_id=moderated_message_id,
                moderator_id=moderator_id,
            )
            return True
        return False

    async def reject_message_by_admin(
        self,
        moderated_message_id: int,
        moderator_id: int,
        comment: str | None = None,
        delete_message: bool = True,
    ) -> bool:
        """Отклонить сообщение админом.

        Args:
            moderated_message_id: ID записи модерации
            moderator_id: ID модератора
            comment: Комментарий
            delete_message: Удалить ли сообщение

        Returns:
            Успешно ли отклонено
        """
        result = await self.moderated_msg_repo.reject_message(
            moderated_message_id, moderator_id, comment, delete_message
        )
        if result:
            await self.session.commit()
            logger.info(
                "Message rejected by admin",
                message_id=moderated_message_id,
                moderator_id=moderator_id,
                deleted=delete_message,
            )
            return True
        return False
