"""system_settings table + user_settings.gold_times

Revision ID: a9c1e3f5b7d0
Revises: f1b3d5a7c9e2
Create Date: 2026-08-29 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a9c1e3f5b7d0"
down_revision: Union[str, None] = "f1b3d5a7c9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "gold_times",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "gold_times")
    op.drop_table("system_settings")
