"""crypto_notify_mode + crypto_coins on user_settings

Revision ID: c5e7a9b1d3f6
Revises: b4d6f8a0c2e5
Create Date: 2026-08-29 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5e7a9b1d3f6"
down_revision: Union[str, None] = "b4d6f8a0c2e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("crypto_notify_mode", sa.String(length=10), nullable=False, server_default="system"),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "crypto_coins",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "crypto_coins")
    op.drop_column("user_settings", "crypto_notify_mode")
