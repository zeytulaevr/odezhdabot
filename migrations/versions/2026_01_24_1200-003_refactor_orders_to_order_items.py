"""Refactor orders to support multiple items via OrderItem table

Revision ID: 003
Revises: 002
Create Date: 2026-01-24 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - create order_items table and migrate data."""

    # 1. Create order_items table
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID товара в заказе"),
        sa.Column("order_id", sa.Integer(), nullable=False, comment="ID заказа"),
        sa.Column("product_id", sa.Integer(), nullable=True, comment="ID товара"),
        sa.Column("size", sa.String(length=10), nullable=False, comment="Размер товара (XS, S, M, L, XL, XXL)"),
        sa.Column("color", sa.String(length=50), nullable=True, comment="Выбранный цвет товара"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1", comment="Количество товара"),
        sa.Column("price_at_order", sa.Numeric(10, 2), nullable=False, comment="Цена товара на момент заказа"),
        sa.Column("product_name", sa.String(length=200), nullable=False, comment="Название товара на момент заказа"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_order_items_order_id_orders"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_order_items_product_id_products"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
        comment="Товары в заказах",
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"])
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"])

    # 2. Migrate existing order data to order_items
    # For each existing order, create a corresponding order_item
    op.execute("""
        INSERT INTO order_items (order_id, product_id, size, color, quantity, price_at_order, product_name, created_at, updated_at)
        SELECT
            o.id,
            o.product_id,
            o.size,
            o.color,
            COALESCE(o.quantity, 1),
            COALESCE(p.price, 0),
            COALESCE(p.name, 'Неизвестный товар'),
            o.created_at,
            o.updated_at
        FROM orders o
        LEFT JOIN products p ON o.product_id = p.id
    """)

    # 3. Drop old columns from orders table
    op.drop_index("ix_orders_product_id", table_name="orders")
    op.drop_constraint("fk_orders_product_id_products", "orders", type_="foreignkey")
    op.drop_column("orders", "quantity")
    op.drop_column("orders", "color")
    op.drop_column("orders", "size")
    op.drop_column("orders", "product_id")


def downgrade() -> None:
    """Downgrade database schema - restore old order structure."""

    # 1. Re-add columns to orders table
    op.add_column("orders", sa.Column("product_id", sa.Integer(), nullable=True, comment="ID товара"))
    op.add_column("orders", sa.Column("size", sa.String(length=10), nullable=True, comment="Размер товара (XS, S, M, L, XL, XXL)"))
    op.add_column("orders", sa.Column("color", sa.String(length=50), nullable=True, comment="Выбранный цвет товара"))
    op.add_column("orders", sa.Column("quantity", sa.Integer(), nullable=True, server_default="1", comment="Количество товара"))

    # 2. Migrate data back (take first item from each order)
    op.execute("""
        UPDATE orders o
        SET
            product_id = oi.product_id,
            size = oi.size,
            color = oi.color,
            quantity = oi.quantity
        FROM (
            SELECT DISTINCT ON (order_id)
                order_id, product_id, size, color, quantity
            FROM order_items
            ORDER BY order_id, id
        ) oi
        WHERE o.id = oi.order_id
    """)

    # 3. Make size NOT NULL after migration
    op.alter_column("orders", "size", nullable=False)

    # 4. Re-create foreign key and index
    op.create_foreign_key("fk_orders_product_id_products", "orders", "products", ["product_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_orders_product_id"), "orders", ["product_id"])

    # 5. Drop order_items table
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")
