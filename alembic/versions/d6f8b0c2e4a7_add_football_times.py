"""add football_times to user_settings

Revision ID: d6f8b0c2e4a7
Revises: c5e7a9b1d3f6
Create Date: 2026-08-29 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d6f8b0c2e4a7"
down_revision: Union[str, None] = "c5e7a9b1d3f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column(
            "football_times",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "football_times")
