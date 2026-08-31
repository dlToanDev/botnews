"""add orders table

Revision ID: c3f9a1b2d4e6
Revises: 4d8f8a24c3da
Create Date: 2026-08-26 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c3f9a1b2d4e6"
down_revision: Union[str, None] = "4d8f8a24c3da"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("item_key", sa.String(length=50), nullable=False),
        sa.Column("item_label", sa.String(length=100), nullable=False),
        sa.Column("modules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)
    op.create_index(op.f("ix_orders_code"), "orders", ["code"], unique=True)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(op.f("ix_orders_created_at"), "orders", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_created_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_code"), table_name="orders")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_table("orders")
