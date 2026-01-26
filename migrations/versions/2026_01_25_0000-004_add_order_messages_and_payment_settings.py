"""Add order messages and payment settings tables

Revision ID: 004
Revises: 003
Create Date: 2026-01-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add order_messages and payment_settings tables."""

    # 1. Create order_messages table
    op.create_table(
        "order_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID сообщения"),
        sa.Column("order_id", sa.Integer(), nullable=False, comment="ID заказа"),
        sa.Column("sender_id", sa.BigInteger(), nullable=False, comment="ID отправителя сообщения"),
        sa.Column("message_text", sa.Text(), nullable=False, comment="Текст сообщения"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Прочитано ли сообщение"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_order_messages_order_id_orders"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], name=op.f("fk_order_messages_sender_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_messages")),
        comment="Сообщения в рамках заказов (чат с клиентом)",
    )
    op.create_index(op.f("ix_order_messages_order_id"), "order_messages", ["order_id"])
    op.create_index(op.f("ix_order_messages_sender_id"), "order_messages", ["sender_id"])
    op.create_index(op.f("ix_order_messages_created_at"), "order_messages", ["created_at"])

    # 2. Create payment_settings table
    op.create_table(
        "payment_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID настройки"),
        sa.Column("payment_details", sa.Text(), nullable=False, comment="Реквизиты для оплаты (номер карты, счёт и т.д.)"),
        sa.Column("payment_instructions", sa.Text(), nullable=True, comment="Инструкции по оплате для клиента"),
        sa.Column("alternative_contact_username", sa.String(length=100), nullable=True, comment="Альтернативный контакт для заказов (@username)"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_settings")),
        comment="Настройки платежей и реквизиты",
    )


def downgrade() -> None:
    """Downgrade database schema - remove order_messages and payment_settings tables."""

    # Drop payment_settings table
    op.drop_table("payment_settings")

    # Drop order_messages table
    op.drop_index(op.f("ix_order_messages_created_at"), table_name="order_messages")
    op.drop_index(op.f("ix_order_messages_sender_id"), table_name="order_messages")
    op.drop_index(op.f("ix_order_messages_order_id"), table_name="order_messages")
    op.drop_table("order_messages")
