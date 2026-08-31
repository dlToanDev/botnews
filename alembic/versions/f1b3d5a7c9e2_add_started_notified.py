"""add started_notified to schedules

Revision ID: f1b3d5a7c9e2
Revises: e7a2c4f8b1d3
Create Date: 2026-08-29 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1b3d5a7c9e2"
down_revision: Union[str, None] = "e7a2c4f8b1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "schedules",
        sa.Column(
            "started_notified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("schedules", "started_notified")
