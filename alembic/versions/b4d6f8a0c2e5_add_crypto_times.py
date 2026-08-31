"""add crypto_times to user_settings

Revision ID: b4d6f8a0c2e5
Revises: a9c1e3f5b7d0
Create Date: 2026-08-29 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4d6f8a0c2e5"
down_revision: Union[str, None] = "a9c1e3f5b7d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column(
            "crypto_times",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "crypto_times")
