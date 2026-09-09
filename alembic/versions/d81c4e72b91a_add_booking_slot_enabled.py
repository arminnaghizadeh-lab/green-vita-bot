"""add booking slot enabled state

Revision ID: d81c4e72b91a
Revises: c7a91e4d5f62
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d81c4e72b91a"
down_revision: str | None = "c7a91e4d5f62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "booking_time_slots",
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "booking_time_slots",
        "is_enabled",
    )
