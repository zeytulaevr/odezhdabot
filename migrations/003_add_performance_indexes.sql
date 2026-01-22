-- Миграция: Добавление индексов для производительности
-- Дата: 2026-01-22
-- Описание: Оптимизация запросов через дополнительные индексы

-- ===========================================
-- Индексы для таблицы users
-- ===========================================

-- Индекс для быстрого поиска активных пользователей
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_active_not_banned
ON users(last_active_at DESC)
WHERE is_banned = false;

-- Композитный индекс для фильтрации по роли и активности
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role_created
ON users(role, created_at DESC);

-- ===========================================
-- Индексы для таблицы orders
-- ===========================================

-- Индекс для сортировки заказов по дате создания
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_created_desc
ON orders(created_at DESC);

-- Композитный индекс для фильтрации по пользователю и статусу
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_status
ON orders(user_id, status);

-- Индекс для фильтрации по статусу с сортировкой по дате
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_status_created
ON orders(status, created_at DESC);

-- Индекс для подсчета заказов пользователя
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orders_user_created
ON orders(user_id, created_at DESC);

-- ===========================================
-- Индексы для таблицы products
-- ===========================================

-- Композитный индекс для активных товаров по категории
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_available_category
ON products(is_available, category_id)
WHERE is_available = true;

-- Индекс для поиска товаров по категории
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_category_created
ON products(category_id, created_at DESC);

-- Индекс для сортировки товаров
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_products_created_desc
ON products(created_at DESC);

-- ===========================================
-- Индексы для таблицы broadcasts
-- ===========================================

-- Композитный индекс для фильтрации по статусу с сортировкой
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_broadcasts_status_created
ON broadcasts(status, created_at DESC);

-- Индекс для поиска рассылок администратора
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_broadcasts_creator_created
ON broadcasts(created_by, created_at DESC);

-- ===========================================
-- Индексы для таблицы reviews
-- ===========================================

-- Индекс для модерации отзывов
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reviews_approved_created
ON reviews(is_approved, created_at DESC);

-- Композитный индекс для отзывов по товару
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reviews_product_approved
ON reviews(product_id, is_approved, created_at DESC);

-- ===========================================
-- Индексы для таблицы categories
-- ===========================================

-- Индекс для активных категорий
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_categories_is_active
ON categories(is_active)
WHERE is_active = true;

-- ===========================================
-- Статистика и VACUUM
-- ===========================================

-- Обновить статистику для планировщика запросов
ANALYZE users;
ANALYZE orders;
ANALYZE products;
ANALYZE broadcasts;
ANALYZE reviews;
ANALYZE categories;

-- Комментарии
COMMENT ON INDEX idx_users_last_active_not_banned IS 'Оптимизация поиска активных пользователей для рассылок';
COMMENT ON INDEX idx_orders_user_status IS 'Быстрый поиск заказов пользователя по статусу';
COMMENT ON INDEX idx_products_available_category IS 'Оптимизация каталога товаров';
COMMENT ON INDEX idx_broadcasts_status_created IS 'Быстрая фильтрация рассылок по статусу';
