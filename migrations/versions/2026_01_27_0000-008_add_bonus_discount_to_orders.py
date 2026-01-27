"""Add bonus_discount field to orders

Revision ID: 008
Revises: 007
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add bonus_discount to orders."""

    # Add bonus_discount field to orders table
    op.add_column(
        "orders",
        sa.Column(
            "bonus_discount",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
            comment="Скидка по бонусам",
        ),
    )


def downgrade() -> None:
    """Downgrade database schema - remove bonus_discount field."""
    op.drop_column("orders", "bonus_discount")
