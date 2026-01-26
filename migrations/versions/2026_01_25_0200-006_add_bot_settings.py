"""Add unified bot_settings table

Revision ID: 006
Revises: 005
Create Date: 2026-01-25 02:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - create unified bot_settings table."""

    # Create bot_settings table
    op.create_table(
        "bot_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID настройки"),
        # Bonus settings
        sa.Column("bonus_purchase_percent", sa.Numeric(5, 2), nullable=False, server_default="5.00", comment="Процент от суммы заказа, начисляемый в виде бонусов"),
        sa.Column("bonus_max_payment_percent", sa.Numeric(5, 2), nullable=False, server_default="50.00", comment="Максимальный процент от суммы заказа, который можно оплатить бонусами"),
        sa.Column("bonus_min_order_amount", sa.Numeric(10, 2), nullable=False, server_default="500.00", comment="Минимальная сумма заказа для начисления бонусов"),
        sa.Column("bonus_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Включена ли бонусная система"),
        # Payment settings
        sa.Column("payment_details", sa.Text(), nullable=True, comment="Реквизиты для оплаты (номер карты, счёт и т.д.)"),
        sa.Column("payment_instructions", sa.Text(), nullable=True, comment="Инструкции по оплате для клиента"),
        sa.Column("alternative_contact_username", sa.String(length=100), nullable=True, comment="Альтернативный контакт для заказов (@username)"),
        # Order settings
        sa.Column("min_order_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00", comment="Минимальная сумма заказа"),
        sa.Column("max_items_per_order", sa.Integer(), nullable=False, server_default="10", comment="Максимальное количество разных товаров в одном заказе"),
        sa.Column("max_quantity_per_item", sa.Integer(), nullable=False, server_default="9", comment="Максимальное количество одного товара"),
        # Notification settings
        sa.Column("welcome_message", sa.Text(), nullable=True, comment="Текст приветственного сообщения"),
        sa.Column("help_message", sa.Text(), nullable=True, comment="Текст сообщения помощи"),
        sa.Column("large_order_message", sa.Text(), nullable=True, comment="Сообщение при попытке заказать 10+ штук одного товара"),
        # Catalog settings
        sa.Column("products_per_page", sa.Integer(), nullable=False, server_default="10", comment="Количество товаров на странице каталога"),
        sa.Column("show_products_without_photos", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Показывать ли товары без фото в каталоге"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bot_settings")),
        comment="Настройки бота",
    )


def downgrade() -> None:
    """Downgrade database schema - remove bot_settings table."""
    op.drop_table("bot_settings")
