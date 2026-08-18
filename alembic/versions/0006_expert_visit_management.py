"""add visit status, scheduling, and admin notes to diagnoses and plant_identifications

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    visit_status = sa.Enum(
        "pending", "scheduled", "completed", "cancelled", name="visitstatus"
    )
    visit_status.create(op.get_bind(), checkfirst=True)

    for table in ("diagnoses", "plant_identifications"):
        op.add_column(
            table,
            sa.Column(
                "visit_status",
                visit_status,
                nullable=False,
                server_default="pending",
            ),
        )
        op.add_column(table, sa.Column("visit_scheduled_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("admin_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    for table in ("diagnoses", "plant_identifications"):
        op.drop_column(table, "admin_notes")
        op.drop_column(table, "visit_scheduled_at")
        op.drop_column(table, "visit_status")

    sa.Enum(name="visitstatus").drop(op.get_bind(), checkfirst=True)
