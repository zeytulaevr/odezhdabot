"""Initial database schema with all tables

Revision ID: 001
Revises:
Create Date: 2026-01-17 17:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Создание расширений PostgreSQL
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Таблица users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="ID пользователя"),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False, comment="Telegram ID пользователя"),
        sa.Column("username", sa.String(length=32), nullable=True, comment="Telegram username"),
        sa.Column("full_name", sa.String(length=255), nullable=False, comment="Полное имя пользователя"),
        sa.Column("phone", sa.String(length=20), nullable=True, comment="Номер телефона"),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user", comment="Роль пользователя"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Заблокирован ли пользователь"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("telegram_id", name=op.f("uq_users_telegram_id")),
        comment="Пользователи Telegram бота",
    )
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"])
    op.create_index(op.f("ix_users_role"), "users", ["role"])

    # Таблица categories
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID категории"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="Название категории"),
        sa.Column("thread_id", sa.BigInteger(), nullable=True, comment="ID ветки (topic) в канале Telegram"),
        sa.Column("channel_message_id", sa.BigInteger(), nullable=True, comment="ID сообщения категории в канале"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Активна ли категория"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата создания категории"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("name", name=op.f("uq_categories_name")),
        comment="Категории товаров в канале",
    )
    op.create_index(op.f("ix_categories_thread_id"), "categories", ["thread_id"])
    op.create_index(op.f("ix_categories_is_active"), "categories", ["is_active"])

    # Таблица products
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID товара"),
        sa.Column("name", sa.String(length=200), nullable=False, comment="Название товара"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание товара"),
        sa.Column("price", sa.DECIMAL(precision=10, scale=2), nullable=False, comment="Цена товара в рублях"),
        sa.Column("category_id", sa.Integer(), nullable=False, comment="ID категории"),
        sa.Column("sizes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]", comment="Доступные размеры товара (массив)"),
        sa.Column("photo_file_id", sa.String(length=255), nullable=True, comment="Telegram file_id фотографии товара"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Активен ли товар"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name=op.f("fk_products_category_id_categories"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        comment="Товары в магазине",
    )
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"])
    op.create_index(op.f("ix_products_is_active"), "products", ["is_active"])

    # Таблица orders
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID заказа"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="ID пользователя"),
        sa.Column("product_id", sa.Integer(), nullable=True, comment="ID товара"),
        sa.Column("size", sa.String(length=10), nullable=False, comment="Размер товара (XS, S, M, L, XL, XXL)"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new", comment="Статус заказа"),
        sa.Column("customer_contact", sa.String(length=500), nullable=False, comment="Контактные данные клиента (телефон, адрес)"),
        sa.Column("admin_notes", sa.Text(), nullable=True, comment="Заметки администратора по заказу"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_orders_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_orders_product_id_products"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        comment="Заказы пользователей",
    )
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"])
    op.create_index(op.f("ix_orders_product_id"), "orders", ["product_id"])
    op.create_index(op.f("ix_orders_status"), "orders", ["status"])
    op.create_index(op.f("ix_orders_created_at"), "orders", ["created_at"])

    # Таблица reviews
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID отзыва"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="ID пользователя"),
        sa.Column("product_id", sa.Integer(), nullable=False, comment="ID товара"),
        sa.Column("text", sa.Text(), nullable=False, comment="Текст отзыва"),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Одобрен ли отзыв для публикации"),
        sa.Column("moderation_status", sa.String(), nullable=False, server_default="pending", comment="Статус модерации"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата создания отзыва"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_reviews_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_reviews_product_id_products"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reviews")),
        comment="Отзывы на товары",
    )
    op.create_index(op.f("ix_reviews_user_id"), "reviews", ["user_id"])
    op.create_index(op.f("ix_reviews_product_id"), "reviews", ["product_id"])
    op.create_index(op.f("ix_reviews_moderation_status"), "reviews", ["moderation_status"])
    op.create_index(op.f("ix_reviews_created_at"), "reviews", ["created_at"])

    # Таблица broadcasts
    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID рассылки"),
        sa.Column("text", sa.Text(), nullable=False, comment="Текст рассылки"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0", comment="Количество отправленных сообщений"),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Фильтры для сегментации аудитории"),
        sa.Column("created_by", sa.BigInteger(), nullable=True, comment="ID администратора, создавшего рассылку"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата создания рассылки"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_broadcasts_created_by_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_broadcasts")),
        comment="Рассылки сообщений",
    )
    op.create_index(op.f("ix_broadcasts_created_by"), "broadcasts", ["created_by"])
    op.create_index(op.f("ix_broadcasts_created_at"), "broadcasts", ["created_at"])

    # Таблица spam_patterns
    op.create_table(
        "spam_patterns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID паттерна"),
        sa.Column("pattern", sa.String(length=500), nullable=False, comment="Паттерн для поиска спама"),
        sa.Column("pattern_type", sa.String(length=20), nullable=False, comment="Тип паттерна (keyword, regex, url)"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Активен ли паттерн"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата создания паттерна"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_spam_patterns")),
        comment="Паттерны для обнаружения спама",
    )
    op.create_index(op.f("ix_spam_patterns_pattern_type"), "spam_patterns", ["pattern_type"])
    op.create_index(op.f("ix_spam_patterns_is_active"), "spam_patterns", ["is_active"])

    # Таблица admin_logs
    op.create_table(
        "admin_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID лога"),
        sa.Column("admin_id", sa.BigInteger(), nullable=True, comment="ID администратора"),
        sa.Column("action", sa.String(length=100), nullable=False, comment="Название действия"),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Детали действия в формате JSON"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время действия"),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], name=op.f("fk_admin_logs_admin_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_logs")),
        comment="Логи действий администраторов",
    )
    op.create_index(op.f("ix_admin_logs_admin_id"), "admin_logs", ["admin_id"])
    op.create_index(op.f("ix_admin_logs_action"), "admin_logs", ["action"])
    op.create_index(op.f("ix_admin_logs_created_at"), "admin_logs", ["created_at"])


def downgrade() -> None:
    """Downgrade database schema."""
    # Удаление таблиц в обратном порядке
    op.drop_table("admin_logs")
    op.drop_table("spam_patterns")
    op.drop_table("broadcasts")
    op.drop_table("reviews")
    op.drop_table("orders")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("users")

    # Удаление расширений
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
