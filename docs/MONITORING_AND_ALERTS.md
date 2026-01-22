# Система мониторинга, логирования и алертов

## Обзор

Полноценная система для production-мониторинга, логирования и оповещения администраторов о критических событиях.

## Компоненты

### 1. Логирование (src/core/logging.py)

**Особенности:**
- Structured logging с **structlog**
- JSON формат для production
- Цветной консольный вывод для development
- Ротация логов (по размеру)
- Автоматический контекст (environment, service)

**Конфигурация:**
```python
# .env
LOG_LEVEL=INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=json         # json или console
LOG_FILE_PATH=logs/bot.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5      # Хранить 5 файлов
```

**Использование:**
```python
from src.core.logging import get_logger

logger = get_logger(__name__)

logger.info("Order created", order_id=42, user_id=123)
logger.error("Failed to process", error=str(e), exc_info=True)
```

### 2. Мониторинг (src/services/monitoring_service.py)

**Собираемые метрики:**

#### Пользователи:
- Всего пользователей
- Активные за 24 часа / 7 дней
- Новые за 24 часа / 7 дней
- По ролям (user, admin, super_admin)
- Заблокированные

#### Заказы:
- Всего заказов
- Новые за 24 часа / 7 дней
- По статусам (new, processing, paid, shipped, completed, cancelled)
- Конверсия (completed / total)

#### Товары:
- Всего товаров
- Активные / неактивные
- По категориям
- Без категории

#### Рассылки:
- Всего рассылок
- Отправлено сообщений
- Доставлено успешно
- Ошибки доставки
- Success rate

#### Отзывы:
- Всего отзывов
- Одобрено / отклонено
- На модерации

**API:**
```python
from src.services.monitoring_service import MonitoringService

service = MonitoringService(session)

# Общая статистика
stats = await service.get_system_stats()

# За период
from datetime import datetime, timedelta
end = datetime.utcnow()
start = end - timedelta(days=7)
period_stats = await service.get_period_stats(start, end)

# Health check
health = await service.get_health_check()
```

### 3. Алерты (src/utils/alerts.py)

**Уровни алертов:**
- **INFO** (ℹ️) - Информационные сообщения
- **WARNING** (⚠️) - Предупреждения
- **ERROR** (❌) - Ошибки
- **CRITICAL** (🚨) - Критические ошибки (уведомляют всех super_admin)

**Автоматические алерты:**
- 10+ ошибок за минуту → критический алерт
- Любая необработанная ошибка → ERROR алерт
- Падение компонентов → CRITICAL алерт

**Использование:**
```python
from src.utils.alerts import AlertManager

# Отправить алерт
await AlertManager.send_alert(
    bot=bot,
    level=AlertLevel.WARNING,
    message="Suspicious activity detected",
    details={"user_id": 123, "action": "spam"}
)

# Быстрые методы
await send_error_alert(bot, error, context)
await send_warning_alert(bot, "Warning message", details)
await send_critical_alert(bot, "Critical issue!", details)

# Трекинг массовых ошибок
await AlertManager.track_error(
    bot=bot,
    error_type="DatabaseError",
    error_message=str(error),
    context={"user_id": 123}
)
```

### 4. Error Handler (src/utils/error_handler.py)

**Функции:**
- Красивые сообщения для пользователей
- Детальные логи для разработчиков
- Автоматические алерты админам
- Маскировка чувствительных данных

**Использование:**
```python
from src.utils.error_handler import ErrorHandler, handle_errors

# Вручную
try:
    # Ваш код
    pass
except Exception as e:
    await ErrorHandler.handle_error(
        error=e,
        event=message,
        bot=bot,
        context={"action": "create_order"},
        send_to_user=True
    )

# Через декоратор
@handle_errors(send_to_user=True)
async def my_handler(message: Message):
    # Ваш код
    # Ошибки обрабатываются автоматически
    pass
```

### 5. Улучшенный Logging Middleware

**Маскировка чувствительных данных:**
- Телефоны: +7912345**
- Email: u***@example.com
- Контакты: не логируются

**Автоматически логирует:**
- Все входящие события
- Время обработки
- Ошибки с traceback
- Отправляет алерты при ошибках

### 6. Статистика для супер-админов

**Доступ:**
/superadmin → Статистика

**Разделы:**
- 📊 Общая статистика - вся система
- 📅 За сегодня - статистика с 00:00
- 📅 За неделю - последние 7 дней
- 📅 За месяц - последние 30 дней
- 💚 Health Check - состояние компонентов

## Структура логов

```json
{
  "timestamp": "2026-01-22T12:35:14.868009",
  "level": "info",
  "event": "Order created",
  "logger": "src.services.order_service",
  "environment": "production",
  "service": "telegram-bot",
  "user_id": 12345,
  "order_id": 42,
  "processing_time": "0.125s"
}
```

## Примеры использования

### Логирование действий

```python
logger.info(
    "User action",
    action="create_order",
    user_id=user.id,
    product_id=product_id,
    amount=amount
)
```

### Отправка алертов

```python
# При критической ошибке
if database_down:
    await send_critical_alert(
        bot=bot,
        message="Database connection lost",
        details={
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### Мониторинг метрик

```python
# В фоновой задаче
async def check_metrics():
    monitoring = MonitoringService(session)
    stats = await monitoring.get_system_stats()

    # Проверяем аномалии
    error_rate = stats["orders"]["failed"] / stats["orders"]["total"]
    if error_rate > 0.1:  # 10% ошибок
        await send_warning_alert(
            bot=bot,
            message=f"High error rate: {error_rate:.1%}",
            details=stats["orders"]
        )
```

### Обработка ошибок

```python
@router.message(Command("order"))
@handle_errors(send_to_user=True)
async def create_order(message: Message, session: AsyncSession):
    # Код создания заказа
    # Любые исключения будут:
    # 1. Залогированы с полным traceback
    # 2. Отправлены админам как алерт
    # 3. Показаны пользователю в понятном виде
    pass
```

## Best Practices

### 1. Не логировать чувствительные данные

❌ Плохо:
```python
logger.info("User registered", phone="+79123456789", email="user@example.com")
```

✅ Хорошо:
```python
logger.info("User registered", user_id=user.id, has_phone=bool(user.phone))
```

### 2. Использовать structured logging

❌ Плохо:
```python
logger.info(f"Order {order_id} created by user {user_id}")
```

✅ Хорошо:
```python
logger.info("Order created", order_id=order_id, user_id=user_id)
```

### 3. Добавлять контекст к ошибкам

❌ Плохо:
```python
except Exception as e:
    logger.error("Error", error=str(e))
```

✅ Хорошо:
```python
except Exception as e:
    logger.error(
        "Failed to create order",
        error=str(e),
        user_id=user_id,
        product_id=product_id,
        exc_info=True  # Добавляет traceback
    )
```

### 4. Использовать соответствующие уровни

```python
logger.debug("Detailed info for debugging")
logger.info("Normal operation")
logger.warning("Something unusual but handled")
logger.error("Error occurred but app continues")
logger.critical("Critical error, app may crash")
```

## Мониторинг в Production

### Проверка логов

```bash
# Последние логи
tail -f logs/bot.log

# Поиск ошибок
grep -i "error" logs/bot.log | tail -20

# JSON query (с jq)
cat logs/bot.log | jq 'select(.level == "error")'
```

### Алерты в Telegram

Все super_admin автоматически получают:
- ❌ ERROR - при каждой ошибке
- 🚨 CRITICAL - при критических проблемах
- ⚠️ WARNING - при подозрительной активности

### Метрики

Проверяйте метрики регулярно:
- Конверсия заказов (норма > 60%)
- Success rate рассылок (норма > 95%)
- Активные пользователи (должен расти)
- Время обработки (< 1s для большинства запросов)

## Расширение

### Добавление новых метрик

Отредактируйте `MonitoringService`:

```python
async def _get_custom_stats(self) -> dict[str, Any]:
    # Ваша логика сбора метрик
    return {"custom_metric": value}
```

### Добавление новых алертов

```python
# В вашем коде
if suspicious_activity:
    await send_warning_alert(
        bot=bot,
        message="Suspicious activity detected",
        details={
            "user_id": user_id,
            "action": action,
            "reason": reason
        }
    )
```

### Кастомные логи

```python
# Добавьте процессор в setup_logging()
def add_custom_context(logger, method_name, event_dict):
    event_dict["custom_field"] = "value"
    return event_dict

# В shared_processors
shared_processors.append(add_custom_context)
```

## Troubleshooting

### Логи не пишутся

Проверьте:
1. Права на директорию `logs/`
2. Настройки в `.env`
3. `LOG_LEVEL` не слишком высокий

### Алерты не приходят

Проверьте:
1. `settings.superadmin_ids` заполнен
2. Бот не заблокирован админами
3. Логи на наличие ошибок отправки

### Высокая нагрузка на БД

Если запросы мониторинга тормозят:
1. Добавьте кэширование метрик
2. Используйте `offset` и `limit` в запросах
3. Создайте индексы на часто запрашиваемые поля

## Production Checklist

- [ ] Включен JSON формат логов
- [ ] Настроена ротация логов
- [ ] Заполнены `superadmin_ids`
- [ ] Проверены алерты (отправьте тестовый)
- [ ] Настроен мониторинг метрик
- [ ] Логи не содержат чувствительных данных
- [ ] Health check endpoint работает
- [ ] Error handling покрывает все критические точки
