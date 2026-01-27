"""Add bonus system (settings, transactions, promocodes)

Revision ID: 005
Revises: 004
Create Date: 2026-01-25 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema - add bonus system tables."""

    # 1. Add bonus_balance to users table
    op.add_column(
        "users",
        sa.Column(
            "bonus_balance",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="0",
            comment="Баланс бонусов пользователя",
        ),
    )

    # 2. Create bonus_settings table
    op.create_table(
        "bonus_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID настройки"),
        sa.Column(
            "purchase_bonus_percent",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="5.00",
            comment="Процент от суммы заказа, начисляемый в виде бонусов (например, 5.00 = 5%)",
        ),
        sa.Column(
            "max_bonus_payment_percent",
            sa.Numeric(5, 2),
            nullable=False,
            server_default="50.00",
            comment="Максимальный процент от суммы заказа, который можно оплатить бонусами (например, 50.00 = 50%)",
        ),
        sa.Column(
            "min_order_amount_for_bonus",
            sa.Numeric(10, 2),
            nullable=False,
            server_default="500.00",
            comment="Минимальная сумма заказа для начисления бонусов",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bonus_settings")),
        comment="Настройки бонусной системы",
    )

    # 3. Create promocodes table
    op.create_table(
        "promocodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID промокода"),
        sa.Column("code", sa.String(length=50), nullable=False, comment="Уникальный код промокода"),
        sa.Column("bonus_amount", sa.Numeric(10, 2), nullable=False, comment="Количество бонусов для начисления"),
        sa.Column("promocode_type", sa.String(length=20), nullable=False, server_default="public", comment="Тип промокода: personal или public"),
        sa.Column("target_user_id", sa.BigInteger(), nullable=True, comment="ID пользователя для персонального промокода"),
        sa.Column("max_activations", sa.Integer(), nullable=True, comment="Максимальное количество активаций (null = неограничено)"),
        sa.Column("activations_count", sa.Integer(), nullable=False, server_default="0", comment="Количество активаций"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True, comment="Дата истечения промокода"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="Активен ли промокод"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание промокода"),
        sa.Column("created_by", sa.BigInteger(), nullable=True, comment="ID администратора, создавшего промокод"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], name=op.f("fk_promocodes_target_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_promocodes_created_by_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promocodes")),
        comment="Промокоды для начисления бонусов",
    )
    op.create_index(op.f("ix_promocodes_code"), "promocodes", ["code"], unique=True)
    op.create_index(op.f("ix_promocodes_is_active"), "promocodes", ["is_active"])
    op.create_index(op.f("ix_promocodes_promocode_type"), "promocodes", ["promocode_type"])

    # 4. Create bonus_transactions table
    op.create_table(
        "bonus_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="ID транзакции"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="ID пользователя"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False, comment="Сумма бонусов (+начисление, -списание)"),
        sa.Column("balance_after", sa.Numeric(10, 2), nullable=False, comment="Баланс бонусов после транзакции"),
        sa.Column("transaction_type", sa.String(length=50), nullable=False, comment="Тип транзакции: purchase, admin_grant, promocode, order_discount, admin_deduct"),
        sa.Column("description", sa.Text(), nullable=True, comment="Описание транзакции"),
        sa.Column("order_id", sa.Integer(), nullable=True, comment="ID связанного заказа"),
        sa.Column("promocode_id", sa.Integer(), nullable=True, comment="ID использованного промокода"),
        sa.Column("admin_id", sa.BigInteger(), nullable=True, comment="ID администратора, выполнившего операцию"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время создания записи"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Дата и время последнего обновления записи"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_bonus_transactions_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_bonus_transactions_order_id_orders"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["promocode_id"], ["promocodes.id"], name=op.f("fk_bonus_transactions_promocode_id_promocodes"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], name=op.f("fk_bonus_transactions_admin_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bonus_transactions")),
        comment="История транзакций бонусов",
    )
    op.create_index(op.f("ix_bonus_transactions_user_id"), "bonus_transactions", ["user_id"])
    op.create_index(op.f("ix_bonus_transactions_transaction_type"), "bonus_transactions", ["transaction_type"])
    op.create_index(op.f("ix_bonus_transactions_created_at"), "bonus_transactions", ["created_at"])


def downgrade() -> None:
    """Downgrade database schema - remove bonus system tables."""

    # Drop bonus_transactions table
    op.drop_index(op.f("ix_bonus_transactions_created_at"), table_name="bonus_transactions")
    op.drop_index(op.f("ix_bonus_transactions_transaction_type"), table_name="bonus_transactions")
    op.drop_index(op.f("ix_bonus_transactions_user_id"), table_name="bonus_transactions")
    op.drop_table("bonus_transactions")

    # Drop promocodes table
    op.drop_index(op.f("ix_promocodes_promocode_type"), table_name="promocodes")
    op.drop_index(op.f("ix_promocodes_is_active"), table_name="promocodes")
    op.drop_index(op.f("ix_promocodes_code"), table_name="promocodes")
    op.drop_table("promocodes")

    # Drop bonus_settings table
    op.drop_table("bonus_settings")

    # Remove bonus_balance from users
    op.drop_column("users", "bonus_balance")
