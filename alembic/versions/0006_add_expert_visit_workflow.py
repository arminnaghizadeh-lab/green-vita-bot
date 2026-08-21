"""add expert visit workflow and visit management fields.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing expert-visit workflow fields used by the Telegram bot.
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
        sa.Column(
            "expert_visit_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "expert_visit_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "expert_visit_scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "diagnoses",
        sa.Column(
            "expert_visit_admin_note",
            sa.Text(),
            nullable=True,
        ),
    )

    # New visit-management workflow shared by diagnoses and plant identification.
    visit_status = sa.Enum(
        "pending",
        "scheduled",
        "completed",
        "cancelled",
        name="visitstatus",
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
        op.add_column(
            table,
            sa.Column(
                "visit_scheduled_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "admin_notes",
                sa.Text(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    for table in ("diagnoses", "plant_identifications"):
        op.drop_column(table, "admin_notes")
        op.drop_column(table, "visit_scheduled_at")
        op.drop_column(table, "visit_status")

    sa.Enum(name="visitstatus").drop(op.get_bind(), checkfirst=True)

    op.drop_column("diagnoses", "expert_visit_admin_note")
    op.drop_column("diagnoses", "expert_visit_scheduled_at")
    op.drop_column("diagnoses", "expert_visit_updated_at")
    op.drop_column("diagnoses", "expert_visit_requested_at")
    op.drop_column("diagnoses", "expert_visit_status")
