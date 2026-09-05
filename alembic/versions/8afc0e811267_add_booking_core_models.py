"""add booking core models

Revision ID: 8afc0e811267
Revises: 0012
Create Date: 2026-09-02 23:17:06.704083
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8afc0e811267'
down_revision: str | None = '0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "booking_services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("price", sa.Numeric(12, 0), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_booking_services_id"), "booking_services", ["id"], unique=False)

    op.create_table(
        "booking_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["booking_services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_schedules_id"), "booking_schedules", ["id"], unique=False)
    op.create_index(op.f("ix_booking_schedules_weekday"), "booking_schedules", ["weekday"], unique=False)

    op.create_table(
        "booking_time_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("schedule_id", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["schedule_id"], ["booking_schedules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schedule_id", "starts_at"),
    )
    op.create_index(op.f("ix_booking_time_slots_id"), "booking_time_slots", ["id"], unique=False)
    op.create_index(op.f("ix_booking_time_slots_starts_at"), "booking_time_slots", ["starts_at"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracking_code", sa.String(32), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("time_slot_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.Enum("ONLINE", "ADMIN", "BOT", name="bookingsource"), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "CONFIRMED", "CANCELLED", "COMPLETED", name="bookingstatus"), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("customer_phone", sa.String(32), nullable=False),
        sa.Column("customer_email", sa.String(320), nullable=True),
        sa.Column("plant_name", sa.String(255), nullable=True),
        sa.Column("plant_description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("base_amount", sa.Numeric(12, 0), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 0), nullable=False),
        sa.Column("final_amount", sa.Numeric(12, 0), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["booking_services.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["time_slot_id"], ["booking_time_slots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tracking_code"),
    )
    op.create_index(op.f("ix_bookings_id"), "bookings", ["id"], unique=False)
    op.create_index(op.f("ix_bookings_tracking_code"), "bookings", ["tracking_code"], unique=True)
    op.create_index(op.f("ix_bookings_status_time_slot_id"), "bookings", ["status", "time_slot_id"], unique=False)
    op.create_index(op.f("ix_bookings_customer_phone"), "bookings", ["customer_phone"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bookings_customer_phone"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_status_time_slot_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_tracking_code"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_id"), table_name="bookings")
    op.drop_table("bookings")

    op.drop_index(op.f("ix_booking_time_slots_starts_at"), table_name="booking_time_slots")
    op.drop_index(op.f("ix_booking_time_slots_id"), table_name="booking_time_slots")
    op.drop_table("booking_time_slots")

    op.drop_index(op.f("ix_booking_schedules_weekday"), table_name="booking_schedules")
    op.drop_index(op.f("ix_booking_schedules_id"), table_name="booking_schedules")
    op.drop_table("booking_schedules")

    op.drop_index(op.f("ix_booking_services_id"), table_name="booking_services")
    op.drop_table("booking_services")
