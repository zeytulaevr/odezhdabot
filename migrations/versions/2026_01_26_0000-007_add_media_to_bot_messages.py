"""Add media support to bot settings messages

Revision ID: 007
Revises: 006
Create Date: 2026-01-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add media fields to bot_settings."""

    # Add media fields for messages
    op.add_column(
        "bot_settings",
        sa.Column(
            "welcome_message_media",
            sa.String(length=200),
            nullable=True,
            comment="File ID медиа для приветственного сообщения",
        ),
    )
    op.add_column(
        "bot_settings",
        sa.Column(
            "help_message_media",
            sa.String(length=200),
            nullable=True,
            comment="File ID медиа для сообщения помощи",
        ),
    )
    op.add_column(
        "bot_settings",
        sa.Column(
            "large_order_message_media",
            sa.String(length=200),
            nullable=True,
            comment="File ID медиа для сообщения о большом заказе",
        ),
    )


def downgrade() -> None:
    """Downgrade database schema - remove media fields."""
    op.drop_column("bot_settings", "large_order_message_media")
    op.drop_column("bot_settings", "help_message_media")
    op.drop_column("bot_settings", "welcome_message_media")
