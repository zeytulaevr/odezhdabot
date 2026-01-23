"""Add colors, fit, media to products and color to orders

Revision ID: 002
Revises: 001
Create Date: 2026-01-23 08:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add new fields to products and orders."""
    # Add colors, fit, and media to products table
    op.add_column(
        "products",
        sa.Column(
            "colors",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
            comment="Доступные цвета товара (массив)",
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "fit",
            sa.String(length=50),
            nullable=True,
            comment="Тип кроя (например: Regular, Slim, Oversize)",
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "media",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
            comment="Медиа файлы товара (до 10 фото/видео): [{type: 'photo'|'video', file_id: '...'}]",
        ),
    )

    # Add color to orders table
    op.add_column(
        "orders",
        sa.Column(
            "color",
            sa.String(length=50),
            nullable=True,
            comment="Выбранный цвет товара",
        ),
    )


def downgrade() -> None:
    """Downgrade database schema - remove new fields."""
    # Remove color from orders
    op.drop_column("orders", "color")

    # Remove colors, fit, and media from products
    op.drop_column("products", "media")
    op.drop_column("products", "fit")
    op.drop_column("products", "colors")
