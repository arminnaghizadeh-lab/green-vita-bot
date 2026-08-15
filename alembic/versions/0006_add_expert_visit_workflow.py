"""add expert visit workflow fields

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diagnoses",
        sa.Column(
            "expert_visit_status",
            sa.String(length=32),
            nullable=False,
            server_default="new",
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column("expert_visit_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "diagnoses",
        sa.Column("expert_visit_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "diagnoses",
        sa.Column("expert_visit_scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "diagnoses",
        sa.Column("expert_visit_admin_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("diagnoses", "expert_visit_admin_note")
    op.drop_column("diagnoses", "expert_visit_scheduled_at")
    op.drop_column("diagnoses", "expert_visit_updated_at")
    op.drop_column("diagnoses", "expert_visit_requested_at")
    op.drop_column("diagnoses", "expert_visit_status")
