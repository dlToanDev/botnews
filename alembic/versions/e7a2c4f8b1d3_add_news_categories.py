"""add news_categories to user_settings

Revision ID: e7a2c4f8b1d3
Revises: c3f9a1b2d4e6
Create Date: 2026-08-28 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e7a2c4f8b1d3"
down_revision: Union[str, None] = "c3f9a1b2d4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column(
            "news_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_settings", "news_categories")
