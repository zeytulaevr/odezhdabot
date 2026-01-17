# Архитектура базы данных

## Обзор

База данных построена на **PostgreSQL** с использованием **SQLAlchemy 2.0** (async) и **asyncpg** драйвера.

## Структура таблиц

### 1. users - Пользователи

```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,  -- Telegram ID пользователя
    username VARCHAR(32),                 -- @username
    full_name VARCHAR(255) NOT NULL,     -- Полное имя из Telegram
    phone VARCHAR(20),                    -- Номер телефона
    role VARCHAR(20) DEFAULT 'user',     -- user | admin | super_admin
    is_banned BOOLEAN DEFAULT false,     -- Забанен ли пользователь
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Индексы:**
- `ix_users_telegram_id` (telegram_id)
- `ix_users_role` (role)

---

### 2. categories - Категории товаров

```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,   -- Название категории
    thread_id BIGINT,                     -- ID ветки в канале Telegram
    channel_message_id BIGINT,            -- ID сообщения категории
    is_active BOOLEAN DEFAULT true,      -- Активна ли категория
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Индексы:**
- `ix_categories_thread_id` (thread_id)
- `ix_categories_is_active` (is_active)

---

### 3. products - Товары

```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,          -- Название товара
    description TEXT,                     -- Описание
    price DECIMAL(10,2) NOT NULL,        -- Цена в рублях
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    sizes JSONB NOT NULL DEFAULT '[]',   -- Массив размеров ["XS", "S", "M", "L"]
    photo_file_id VARCHAR(255),          -- Telegram file_id фото
    is_active BOOLEAN DEFAULT true,      -- Активен ли товар
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Индексы:**
- `ix_products_category_id` (category_id)
- `ix_products_is_active` (is_active)

**Пример JSONB sizes:**
```json
["XS", "S", "M", "L", "XL", "XXL"]
```

---

### 4. orders - Заказы

```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    size VARCHAR(10) NOT NULL,           -- Размер товара
    status VARCHAR(20) DEFAULT 'new',    -- new | processing | paid | shipped | completed | cancelled
    customer_contact VARCHAR(500) NOT NULL, -- Контакты (телефон, адрес)
    admin_notes TEXT,                    -- Заметки администратора
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Индексы:**
- `ix_orders_user_id` (user_id)
- `ix_orders_product_id` (product_id)
- `ix_orders_status` (status)
- `ix_orders_created_at` (created_at)

**Статусы:**
- `new` - Новый заказ
- `processing` - В обработке
- `paid` - Оплачен
- `shipped` - Отправлен
- `completed` - Завершён
- `cancelled` - Отменён

---

### 5. reviews - Отзывы на товары

```sql
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    text TEXT NOT NULL,                  -- Текст отзыва
    is_approved BOOLEAN DEFAULT false,   -- Одобрен ли отзыв
    moderation_status VARCHAR DEFAULT 'pending', -- pending | approved | rejected | flagged
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Индексы:**
- `ix_reviews_user_id` (user_id)
- `ix_reviews_product_id` (product_id)
- `ix_reviews_moderation_status` (moderation_status)
- `ix_reviews_created_at` (created_at)

---

### 6. broadcasts - Рассылки

```sql
CREATE TABLE broadcasts (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,                  -- Текст рассылки
    sent_count INTEGER DEFAULT 0,        -- Количество отправленных
    filters JSONB,                       -- Фильтры сегментации
    created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Индексы:**
- `ix_broadcasts_created_by` (created_by)
- `ix_broadcasts_created_at` (created_at)

**Пример JSONB filters:**
```json
{
  "role": "user",
  "created_after": "2024-01-01",
  "has_orders": true
}
```

---

### 7. spam_patterns - Паттерны спама

```sql
CREATE TABLE spam_patterns (
    id SERIAL PRIMARY KEY,
    pattern VARCHAR(500) NOT NULL,       -- Паттерн для поиска
    pattern_type VARCHAR(20) NOT NULL,   -- keyword | regex | url
    is_active BOOLEAN DEFAULT true,      -- Активен ли паттерн
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Индексы:**
- `ix_spam_patterns_pattern_type` (pattern_type)
- `ix_spam_patterns_is_active` (is_active)

---

### 8. admin_logs - Логи действий администраторов

```sql
CREATE TABLE admin_logs (
    id SERIAL PRIMARY KEY,
    admin_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,        -- Название действия
    details JSONB,                       -- Детали действия
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Индексы:**
- `ix_admin_logs_admin_id` (admin_id)
- `ix_admin_logs_action` (action)
- `ix_admin_logs_created_at` (created_at)

**Пример JSONB details:**
```json
{
  "order_id": 123,
  "old_status": "new",
  "new_status": "processing"
}
```

---

## Диаграмма связей

```
users (1) ────< (M) orders
users (1) ────< (M) reviews
users (1) ────< (M) broadcasts (создатель)
users (1) ────< (M) admin_logs

categories (1) ────< (M) products

products (1) ────< (M) orders
products (1) ────< (M) reviews
```

---

## Репозитории

Каждая таблица имеет свой репозиторий с CRUD операциями и специфичными методами:

### UserRepository
- `get_by_telegram_id()` - поиск по Telegram ID
- `get_or_create()` - получить или создать пользователя
- `get_all_admins()` - все администраторы
- `ban_user()` / `unban_user()` - блокировка

### CategoryRepository
- `get_active_categories()` - активные категории
- `get_by_thread_id()` - поиск по ID ветки канала
- `toggle_active()` - переключить активность

### ProductRepository
- `get_active_products()` - активные товары
- `get_by_category_id()` - товары по категории
- `search_by_name()` - поиск по названию

### OrderRepository
- `get_user_orders()` - заказы пользователя
- `get_by_status()` - заказы по статусу
- `create_order()` - создать заказ
- `update_status()` - обновить статус
- `add_admin_notes()` - добавить заметки

### ReviewRepository
- `get_pending_reviews()` - отзывы на модерации
- `approve_review()` / `reject_review()` - модерация
- `flag_review()` - пометить как подозрительный

### BroadcastRepository
- `create_broadcast()` - создать рассылку
- `increment_sent_count()` - увеличить счётчик
- `get_recent_broadcasts()` - недавние рассылки

### SpamPatternRepository
- `get_active_patterns()` - активные паттерны
- `get_by_type()` - по типу (keyword/regex/url)

### AdminLogRepository
- `log_action()` - записать действие в лог
- `get_admin_actions()` - действия администратора

---

## Миграции

Для управления схемой БД используется **Alembic**.

### Применить миграции:
```bash
poetry run alembic upgrade head
```

### Создать новую миграцию:
```bash
poetry run alembic revision --autogenerate -m "описание"
```

### Откатить миграцию:
```bash
poetry run alembic downgrade -1
```

---

## PostgreSQL расширения

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Для полнотекстового поиска
```

---

## Особенности

1. **Асинхронность** - все операции через asyncpg
2. **JSONB поля** - гибкое хранение сложных данных (sizes, filters, details)
3. **Индексы** - на часто используемые поля для быстрого поиска
4. **Soft delete** - через флаги is_active/is_banned
5. **Каскадное удаление** - автоматическая очистка связанных данных
6. **Timestamps** - автоматическое отслеживание created_at/updated_at

---

## Примеры использования

### Создание пользователя

```python
user_repo = UserRepository(session)
user, is_new = await user_repo.get_or_create(
    telegram_id=123456789,
    full_name="Иван Иванов",
    username="ivan"
)
```

### Создание заказа

```python
order_repo = OrderRepository(session)
order = await order_repo.create_order(
    user_id=1,
    product_id=5,
    size="M",
    customer_contact="+7 900 123-45-67, г. Москва, ул. Ленина 1"
)
```

### Модерация отзыва

```python
review_repo = ReviewRepository(session)
await review_repo.approve_review(review_id=10)
```

### Логирование действия админа

```python
log_repo = AdminLogRepository(session)
await log_repo.log_action(
    admin_id=1,
    action="order_status_changed",
    details={"order_id": 123, "old_status": "new", "new_status": "processing"}
)
```
