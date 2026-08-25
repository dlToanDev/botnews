"""init core tables

Revision ID: 458a856d62d9
Revises:
Create Date: 2026-08-25 02:33:02.054425
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "458a856d62d9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_expires_at"), "users", ["expires_at"], unique=False)
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=True)
    op.create_table(
        "logs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_logs_action"), "logs", ["action"], unique=False)
    op.create_index(op.f("ix_logs_created_at"), "logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_logs_user_id"), "logs", ["user_id"], unique=False)
    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("recurrence", sa.String(length=20), nullable=False),
        sa.Column("recur_days", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reminder_minutes", sa.Integer(), nullable=False),
        sa.Column("is_notified", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedules_start_time"), "schedules", ["start_time"], unique=False)
    op.create_index(op.f("ix_schedules_user_id"), "schedules", ["user_id"], unique=False)
    op.create_table(
        "user_settings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=False),
        sa.Column("daily_digest_time", sa.Time(), nullable=False),
        sa.Column("reminder_minutes", sa.Integer(), nullable=False),
        sa.Column("crypto_watchlist", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gold_alert_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("news_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("favorite_teams", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_index(op.f("ix_schedules_user_id"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_start_time"), table_name="schedules")
    op.drop_table("schedules")
    op.drop_index(op.f("ix_logs_user_id"), table_name="logs")
    op.drop_index(op.f("ix_logs_created_at"), table_name="logs")
    op.drop_index(op.f("ix_logs_action"), table_name="logs")
    op.drop_table("logs")
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_index(op.f("ix_users_expires_at"), table_name="users")
    op.drop_table("users")
