# Code Style Guide

## Общие принципы

### 1. Чистота и читаемость
- Код пишется один раз, читается много раз
- Явное лучше неявного
- Простое лучше сложного

### 2. Размер файлов
- Максимум 500 строк на файл
- Один класс/сервис = одна ответственность (Single Responsibility Principle)
- Разбивайте большие файлы на модули

### 3. Именование
```python
# Классы - PascalCase
class OrderService:
    pass

# Функции и методы - snake_case
async def get_user_orders():
    pass

# Константы - UPPER_SNAKE_CASE
MAX_ORDERS_PER_PAGE = 50

# Приватные методы - с подчеркиванием
def _internal_helper():
    pass

# Переменные - snake_case, описательные
user_orders = await get_user_orders()
```

## Type Hints

### Обязательно везде

```python
from typing import Any

# ✅ Хорошо
async def get_user(user_id: int) -> User | None:
    """Get user by ID."""
    pass

async def process_orders(
    user: User,
    limit: int = 10,
) -> list[Order]:
    """Process user orders."""
    pass

def format_message(
    text: str,
    **kwargs: Any,
) -> str:
    """Format message with kwargs."""
    pass

# ❌ Плохо
async def get_user(user_id):  # Нет type hints
    pass
```

## Docstrings (Google Style)

### Для всех публичных методов

```python
async def create_order(
    user_id: int,
    product_id: int,
    quantity: int = 1,
) -> Order:
    """Create a new order.

    Args:
        user_id: ID of the user placing the order
        product_id: ID of the product to order
        quantity: Number of items to order (default: 1)

    Returns:
        Created Order object

    Raises:
        ValueError: If quantity is less than 1
        ProductNotFoundError: If product doesn't exist

    Example:
        >>> order = await create_order(123, 456, quantity=2)
        >>> print(order.id)
        789
    """
    if quantity < 1:
        raise ValueError("Quantity must be at least 1")

    # Implementation...
    return order
```

## Async/Await

### Правильное использование

```python
# ✅ Хорошо - все I/O асинхронно
async def get_user_data(user_id: int) -> dict:
    """Get user data from database."""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

# ❌ Плохо - синхронный вызов блокирует event loop
async def get_user_data(user_id: int) -> dict:
    time.sleep(1)  # Блокирует!
    return {}

# ✅ Хорошо - используем asyncio.sleep
async def get_user_data(user_id: int) -> dict:
    await asyncio.sleep(1)
    return {}
```

## Обработка ошибок

### Try/Except везде где нужно

```python
# ✅ Хорошо - специфичные исключения
async def create_order(user_id: int, product_id: int) -> Order:
    """Create order with proper error handling."""
    try:
        product = await get_product(product_id)
        if not product:
            raise ProductNotFoundError(f"Product {product_id} not found")

        order = Order(user_id=user_id, product_id=product_id)
        session.add(order)
        await session.commit()

        logger.info(
            "Order created",
            order_id=order.id,
            user_id=user_id,
            product_id=product_id,
        )

        return order

    except ProductNotFoundError:
        logger.warning("Product not found", product_id=product_id)
        raise

    except Exception as e:
        logger.error(
            "Failed to create order",
            error=str(e),
            user_id=user_id,
            product_id=product_id,
            exc_info=True,
        )
        raise

# ❌ Плохо - голый except
try:
    # code
except:  # Ловит всё, включая KeyboardInterrupt!
    pass

# ❌ Плохо - не логируем ошибку
try:
    # code
except Exception:
    pass  # Молчаливо игнорируем
```

## База данных

### Connection Pooling

```python
# ✅ Хорошо - используем session из middleware
async def get_users(session: AsyncSession) -> list[User]:
    """Get all users."""
    result = await session.execute(select(User))
    return list(result.scalars().all())

# ❌ Плохо - создаем новое соединение каждый раз
async def get_users() -> list[User]:
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        return list(result.scalars().all())
```

### Prepared Statements (автоматически с SQLAlchemy)

```python
# ✅ Хорошо - защищено от SQL injection
user_id = request.user_id
result = await session.execute(
    select(User).where(User.id == user_id)
)

# ❌ Плохо - SQL injection уязвимость
query = f"SELECT * FROM users WHERE id = {user_id}"
```

### Транзакции

```python
# ✅ Хорошо - используем транзакции
async def transfer_order(order_id: int, new_user_id: int) -> Order:
    """Transfer order to another user."""
    async with session.begin():  # Транзакция
        order = await session.get(Order, order_id)
        order.user_id = new_user_id

        # Создаем лог
        log = OrderLog(order_id=order_id, action="transferred")
        session.add(log)

        await session.commit()  # Обе операции или ни одной

    return order
```

### Избегаем N+1 запросов

```python
# ✅ Хорошо - eager loading
result = await session.execute(
    select(Order)
    .options(selectinload(Order.product))  # Загружаем связанные данные
    .where(Order.user_id == user_id)
)
orders = result.scalars().all()

# Теперь можно использовать order.product без дополнительных запросов
for order in orders:
    print(order.product.name)  # Нет запроса к БД

# ❌ Плохо - N+1 запросов
result = await session.execute(
    select(Order).where(Order.user_id == user_id)
)
orders = result.scalars().all()

for order in orders:
    print(order.product.name)  # Каждая итерация = новый запрос!
```

## Логирование

### Structured Logging

```python
from src.core.logging import get_logger

logger = get_logger(__name__)

# ✅ Хорошо - structured log с контекстом
logger.info(
    "Order created",
    order_id=order.id,
    user_id=user.id,
    product_id=product.id,
    amount=order.amount,
)

# ✅ Хорошо - логирование ошибок
try:
    await create_order()
except Exception as e:
    logger.error(
        "Failed to create order",
        error=str(e),
        user_id=user_id,
        exc_info=True,  # Добавляет traceback
    )

# ❌ Плохо - строковая интерполяция
logger.info(f"Order {order.id} created for user {user.id}")

# ❌ Плохо - логируем чувствительные данные
logger.info("User registered", phone="+79123456789", email="user@example.com")

# ✅ Хорошо - маскируем чувствительные данные
logger.info("User registered", user_id=user.id, has_phone=bool(user.phone))
```

### Уровни логирования

```python
# DEBUG - детальная информация для отладки
logger.debug("Processing batch", batch_size=len(items), items=items[:5])

# INFO - обычные операции
logger.info("User logged in", user_id=user.id)

# WARNING - что-то необычное, но обработанное
logger.warning("Rate limit approaching", current=98, limit=100)

# ERROR - ошибка, но приложение продолжает работу
logger.error("Failed to send email", user_id=user.id, error=str(e))

# CRITICAL - критическая ошибка, приложение может упасть
logger.critical("Database connection lost", error=str(e))
```

## Безопасность

### Валидация входных данных

```python
from pydantic import BaseModel, Field, validator

class OrderCreate(BaseModel):
    """Order creation schema."""

    product_id: int = Field(gt=0)  # > 0
    quantity: int = Field(ge=1, le=100)  # 1-100
    notes: str | None = Field(None, max_length=500)

    @validator('notes')
    def validate_notes(cls, v):
        """Validate notes don't contain spam."""
        if v and any(spam in v.lower() for spam in ['viagra', 'casino']):
            raise ValueError("Notes contain prohibited content")
        return v
```

### Нет хардкода секретов

```python
# ✅ Хорошо - используем переменные окружения
from src.core.config import settings

bot_token = settings.bot_token
db_password = settings.database_password

# ❌ Плохо - хардкод
bot_token = "1234567890:ABCdefGHI..."
db_password = "my_secret_password"
```

## Производительность

### Batch Operations

```python
# ✅ Хорошо - batch insert
users = [User(name=f"User {i}") for i in range(100)]
session.add_all(users)  # Одна операция
await session.commit()

# ❌ Плохо - по одному
for i in range(100):
    user = User(name=f"User {i}")
    session.add(user)
    await session.commit()  # 100 операций!
```

### Кэширование

```python
from functools import lru_cache

# ✅ Хорошо - кэширование статических данных
@lru_cache(maxsize=128)
def get_status_name(status: str) -> str:
    """Get human-readable status name."""
    return STATUS_NAMES.get(status, status)

# Для async функций используйте aiocache или redis
```

## Тестируемость

### Dependency Injection

```python
# ✅ Хорошо - легко тестировать с моками
class OrderService:
    """Order management service."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(self, user_id: int) -> Order:
        # ...

# В тестах
async def test_create_order():
    mock_session = MagicMock(spec=AsyncSession)
    service = OrderService(mock_session)
    await service.create_order(123)

# ❌ Плохо - жестко связано с глобальным состоянием
class OrderService:
    async def create_order(self, user_id: int) -> Order:
        session = get_global_session()  # Трудно замокать
```

## Импорты (isort)

```python
# 1. Стандартная библиотека
import asyncio
import logging
from datetime import datetime
from typing import Any

# 2. Сторонние библиотеки
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from sqlalchemy import select

# 3. Локальные импорты
from src.core.config import settings
from src.core.logging import get_logger
from src.database.models import User
from src.services.order_service import OrderService
```

## Форматирование (Black)

```python
# Black автоматически форматирует код
# Настройки в pyproject.toml:
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

# Запуск:
black src/
```

## Линтинг (Ruff)

```python
# Ruff проверяет код на ошибки
# Настройки в pyproject.toml:
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # line too long (обрабатывается Black)

# Запуск:
ruff check src/
```

## Комментарии

### Комментируйте "почему", а не "что"

```python
# ✅ Хорошо - объясняем причину
# Используем 20 msg/sec вместо 30 для предотвращения rate limit от Telegram
MESSAGES_PER_SECOND = 20

# ❌ Плохо - очевидно из кода
# Устанавливаем messages_per_second в 20
MESSAGES_PER_SECOND = 20

# ✅ Хорошо - объясняем сложную логику
# Telegram API возвращает ошибку 429 при превышении лимита.
# Мы ждем retry_after секунд и пытаемся снова.
if isinstance(error, TelegramRetryAfter):
    await asyncio.sleep(error.retry_after)
    return await self._send_message(user_id, text)
```

## Checklist для code review

- [ ] Все функции имеют type hints
- [ ] Все публичные методы имеют docstrings
- [ ] Нет синхронных блокирующих вызовов в async функциях
- [ ] Ошибки обрабатываются с proper logging
- [ ] Нет SQL injection уязвимостей
- [ ] Чувствительные данные не логируются
- [ ] Используются транзакции где нужно
- [ ] Нет N+1 запросов
- [ ] Batch operations где возможно
- [ ] Код отформатирован (Black)
- [ ] Импорты отсортированы (isort)
- [ ] Линтер не показывает ошибок (Ruff)
- [ ] Тесты написаны и проходят
- [ ] Документация обновлена
