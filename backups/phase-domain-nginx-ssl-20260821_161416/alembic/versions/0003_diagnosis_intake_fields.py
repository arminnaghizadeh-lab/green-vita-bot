"""add intake fields and expert visit flag to diagnoses

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("diagnoses", sa.Column("plant_name_input", sa.String(255), nullable=True))
    op.add_column("diagnoses", sa.Column("user_notes", sa.Text(), nullable=True))
    op.add_column(
        "diagnoses",
        sa.Column(
            "expert_visit_requested", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("diagnoses", "expert_visit_requested")
    op.drop_column("diagnoses", "user_notes")
    op.drop_column("diagnoses", "plant_name_input")
