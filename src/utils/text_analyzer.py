"""Утилиты для анализа текста на спам и подозрительный контент."""

import re
from typing import NamedTuple
from urllib.parse import urlparse


class AnalysisResult(NamedTuple):
    """Результат анализа текста."""

    spam_score: int  # 0-100
    reasons: list[str]  # Список причин подозрения
    matched_patterns: list[str]  # Сработавшие паттерны


class TextAnalyzer:
    """Анализатор текста для обнаружения спама."""

    # Подозрительные домены
    SUSPICIOUS_DOMAINS = [
        "bit.ly",
        "goo.gl",
        "tinyurl.com",
        "ow.ly",
        "t.co",
        "is.gd",
    ]

    # Паттерны для обнаружения контактов
    CONTACT_PATTERNS = [
        r"\+?\d{1,3}[\s-]?\(?\d{2,4}\)?[\s-]?\d{2,4}[\s-]?\d{2,4}",  # Телефоны
        r"@\w+",  # Telegram username
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",  # Email
    ]

    # Спам-маркеры (увеличивают score)
    SPAM_MARKERS = [
        (r"заработ(ок|ать|айте)", 15),  # Заработок
        (r"(пассивн|доп)[а-я]*\s*(доход|заработок)", 20),  # Пассивный доход
        (r"(крипто|bitcoin|btc|eth)", 15),  # Криптовалюта
        (r"(инвест|вклад|дивиденд)", 15),  # Инвестиции
        (r"(ставки|казино|слот)", 20),  # Азартные игры
        (r"(\\bMLM\\b|сетевой маркетинг)", 25),  # MLM
        (r"(бесплатн[а-я]*|халяв[а-я]*)", 10),  # Бесплатно
        (r"(жми|переходи|подписывайся)\s*(сюда|здесь|по ссылке)", 15),  # CTA
        (r"(гарантир[а-я]*|100%)", 10),  # Гарантии
        (r"(подарок|приз|выигр[а-я]*)", 12),  # Подарки/призы
    ]

    @staticmethod
    def extract_urls(text: str) -> list[str]:
        """Извлечь URL из текста.

        Args:
            text: Текст для анализа

        Returns:
            Список найденных URL
        """
        url_pattern = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        return re.findall(url_pattern, text)

    @classmethod
    def check_suspicious_links(cls, text: str) -> tuple[int, list[str]]:
        """Проверить ссылки на подозрительность.

        Args:
            text: Текст для проверки

        Returns:
            Кортеж (score, reasons)
        """
        urls = cls.extract_urls(text)
        score = 0
        reasons = []

        if not urls:
            return 0, []

        # Много ссылок подозрительно
        if len(urls) > 2:
            score += 20
            reasons.append(f"Много ссылок ({len(urls)})")

        # Проверка доменов
        for url in urls:
            try:
                domain = urlparse(url).netloc
                if any(susp in domain for susp in cls.SUSPICIOUS_DOMAINS):
                    score += 25
                    reasons.append(f"Подозрительный домен: {domain}")
            except Exception:
                pass

        return min(score, 100), reasons

    @classmethod
    def check_contacts(cls, text: str) -> tuple[int, list[str]]:
        """Проверить наличие контактов.

        Args:
            text: Текст для проверки

        Returns:
            Кортеж (score, reasons)
        """
        score = 0
        reasons = []

        for pattern in cls.CONTACT_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                score += 15
                reasons.append(f"Контактная информация: {matches[0][:20]}...")

        return min(score, 100), reasons

    @classmethod
    def check_spam_markers(cls, text: str) -> tuple[int, list[str]]:
        """Проверить текст на спам-маркеры.

        Args:
            text: Текст для проверки

        Returns:
            Кортеж (score, reasons)
        """
        score = 0
        reasons = []
        text_lower = text.lower()

        for pattern, marker_score in cls.SPAM_MARKERS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += marker_score
                reasons.append(f"Спам-маркер: {pattern}")

        return min(score, 100), reasons

    @classmethod
    def check_caps_ratio(cls, text: str) -> tuple[int, list[str]]:
        """Проверить соотношение заглавных букв.

        Args:
            text: Текст для проверки

        Returns:
            Кортеж (score, reasons)
        """
        if len(text) < 10:
            return 0, []

        letters = [c for c in text if c.isalpha()]
        if not letters:
            return 0, []

        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)

        if caps_ratio > 0.5:
            score = int(caps_ratio * 30)
            return score, [f"Много заглавных букв ({int(caps_ratio * 100)}%)"]

        return 0, []

    @classmethod
    def check_repeated_chars(cls, text: str) -> tuple[int, list[str]]:
        """Проверить повторяющиеся символы.

        Args:
            text: Текст для проверки

        Returns:
            Кортеж (score, reasons)
        """
        # Паттерн для повторяющихся символов (3+ подряд)
        pattern = r"(.)\1{2,}"
        matches = re.findall(pattern, text)

        if matches:
            score = min(len(matches) * 10, 30)
            return score, [f"Повторяющиеся символы: {len(matches)} раз"]

        return 0, []

    @classmethod
    def check_emoji_ratio(cls, text: str) -> tuple[int, list[str]]:
        """Проверить соотношение эмодзи.

        Args:
            text: Текст для проверки

        Returns:
            Кортеж (score, reasons)
        """
        # Упрощенная проверка на эмодзи через Unicode ranges
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE,
        )

        emojis = emoji_pattern.findall(text)
        if len(text) < 10:
            return 0, []

        emoji_ratio = len("".join(emojis)) / len(text)

        if emoji_ratio > 0.3:
            score = int(emoji_ratio * 40)
            return score, [f"Много эмодзи ({int(emoji_ratio * 100)}%)"]

        return 0, []

    @classmethod
    def analyze(cls, text: str) -> AnalysisResult:
        """Полный анализ текста.

        Args:
            text: Текст для анализа

        Returns:
            Результат анализа
        """
        total_score = 0
        all_reasons = []

        # Проверки
        checks = [
            cls.check_suspicious_links(text),
            cls.check_contacts(text),
            cls.check_spam_markers(text),
            cls.check_caps_ratio(text),
            cls.check_repeated_chars(text),
            cls.check_emoji_ratio(text),
        ]

        for score, reasons in checks:
            total_score += score
            all_reasons.extend(reasons)

        # Ограничиваем максимум
        total_score = min(total_score, 100)

        return AnalysisResult(
            spam_score=total_score,
            reasons=all_reasons,
            matched_patterns=[],  # Будет заполнено паттернами из БД
        )


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Вычислить простое сходство двух текстов.

    Args:
        text1: Первый текст
        text2: Второй текст

    Returns:
        Коэффициент сходства 0.0-1.0
    """
    # Упрощенный алгоритм - сравнение нормализованных текстов
    def normalize(text: str) -> set:
        # Убираем пунктуацию, приводим к нижнему регистру
        text = re.sub(r"[^\w\s]", "", text.lower())
        return set(text.split())

    words1 = normalize(text1)
    words2 = normalize(text2)

    if not words1 or not words2:
        return 0.0

    # Коэффициент Жаккара
    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0
