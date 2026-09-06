"""add booking slot assignments

Revision ID: b3f7c91a2d44
Revises: 8afc0e811267
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b3f7c91a2d44"
down_revision: str | None = "8afc0e811267"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "booking_slot_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("time_slot_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["time_slot_id"],
            ["booking_time_slots.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "booking_id",
            "time_slot_id",
            name="booking_slot_assignments_booking_slot_key",
        ),
        sa.UniqueConstraint(
            "time_slot_id",
            name="booking_slot_assignments_time_slot_key",
        ),
    )

    op.create_index(
        "ix_booking_slot_assignments_booking_id",
        "booking_slot_assignments",
        ["booking_id"],
        unique=False,
    )

    op.create_index(
        "ix_booking_slot_assignments_time_slot_id",
        "booking_slot_assignments",
        ["time_slot_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_booking_slot_assignments_time_slot_id",
        table_name="booking_slot_assignments",
    )

    op.drop_index(
        "ix_booking_slot_assignments_booking_id",
        table_name="booking_slot_assignments",
    )

    op.drop_table("booking_slot_assignments")
