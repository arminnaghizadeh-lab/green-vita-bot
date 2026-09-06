"""backfill legacy booking slot assignments

Revision ID: c7a91e4d5f62
Revises: b3f7c91a2d44
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "c7a91e4d5f62"
down_revision: str | None = "b3f7c91a2d44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()

    op.create_table(
        "booking_slot_assignment_backfill_log",
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("booking_id"),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            ondelete="CASCADE",
        ),
    )

    # Assignmentهای رزروهای لغوشده دیگر نباید Slot را اشغال نگه دارند.
    cancelled_slots = connection.execute(
        sa.text("""
            SELECT
                a.time_slot_id
            FROM booking_slot_assignments a
            JOIN bookings b
                ON b.id = a.booking_id
            WHERE b.status = 'CANCELLED'
            FOR UPDATE
        """)
    ).mappings().all()

    for row in cancelled_slots:
        connection.execute(
            sa.text("""
                UPDATE booking_time_slots
                SET is_available = true
                WHERE id = :slot_id
            """),
            {"slot_id": row["time_slot_id"]},
        )

    connection.execute(
        sa.text("""
            DELETE FROM booking_slot_assignments a
            USING bookings b
            WHERE a.booking_id = b.id
              AND b.status = 'CANCELLED'
        """)
    )

    bookings = connection.execute(
        sa.text("""
            SELECT
                b.id,
                b.time_slot_id
            FROM bookings b
            LEFT JOIN booking_slot_assignments a
                ON a.booking_id = b.id
            WHERE a.id IS NULL
              AND b.status IN ('PENDING', 'CONFIRMED')
            ORDER BY b.id
            FOR UPDATE OF b
        """)
    ).mappings().all()

    for booking in bookings:
        booking_id = booking["id"]
        start_slot_id = booking["time_slot_id"]

        start_slot = connection.execute(
            sa.text("""
                SELECT
                    id,
                    schedule_id,
                    starts_at,
                    ends_at,
                    is_available
                FROM booking_time_slots
                WHERE id = :slot_id
                FOR UPDATE
            """),
            {"slot_id": start_slot_id},
        ).mappings().first()

        if start_slot is None:
            raise RuntimeError(
                f"Booking {booking_id} references missing "
                f"slot {start_slot_id}"
            )

        if not start_slot["is_available"]:
            # This is expected for a legacy active booking:
            # its original slot is already marked unavailable.
            pass

        connection.execute(
            sa.text("""
                INSERT INTO booking_slot_assignments
                    (booking_id, time_slot_id, kind)
                VALUES
                    (:booking_id, :time_slot_id, 'RESERVED')
            """),
            {
                "booking_id": booking_id,
                "time_slot_id": start_slot_id,
            },
        )

        buffer_slots = connection.execute(
            sa.text("""
                SELECT
                    id,
                    starts_at,
                    ends_at,
                    is_available
                FROM booking_time_slots
                WHERE schedule_id = :schedule_id
                  AND starts_at >= :buffer_start
                  AND starts_at < :buffer_start + INTERVAL '2 hours'
                ORDER BY starts_at
                FOR UPDATE
            """),
            {
                "schedule_id": start_slot["schedule_id"],
                "buffer_start": start_slot["ends_at"],
            },
        ).mappings().all()

        if len(buffer_slots) != 2:
            raise RuntimeError(
                f"Legacy booking {booking_id} does not have "
                f"exactly two buffer slots."
            )

        expected_start = start_slot["ends_at"]

        for slot in buffer_slots:
            if slot["starts_at"] != expected_start:
                raise RuntimeError(
                    f"Legacy booking {booking_id} has "
                    f"non-contiguous buffer slots."
                )

            if not slot["is_available"]:
                raise RuntimeError(
                    f"Legacy booking {booking_id} cannot be backfilled "
                    f"because buffer slot {slot['id']} is unavailable."
                )

            connection.execute(
                sa.text("""
                    INSERT INTO booking_slot_assignments
                        (booking_id, time_slot_id, kind)
                    VALUES
                        (:booking_id, :time_slot_id, 'BUFFER')
                """),
                {
                    "booking_id": booking_id,
                    "time_slot_id": slot["id"],
                },
            )

            connection.execute(
                sa.text("""
                    UPDATE booking_time_slots
                    SET is_available = false
                    WHERE id = :slot_id
                """),
                {"slot_id": slot["id"]},
            )

            expected_start = slot["ends_at"]

        connection.execute(
            sa.text("""
                INSERT INTO booking_slot_assignment_backfill_log
                    (booking_id)
                VALUES
                    (:booking_id)
            """),
            {"booking_id": booking_id},
        )


def downgrade() -> None:
    connection = op.get_bind()

    booking_rows = connection.execute(
        sa.text("""
            SELECT booking_id
            FROM booking_slot_assignment_backfill_log
            ORDER BY booking_id
        """)
    ).mappings().all()

    for row in booking_rows:
        booking_id = row["booking_id"]

        slot_rows = connection.execute(
            sa.text("""
                SELECT time_slot_id
                FROM booking_slot_assignments
                WHERE booking_id = :booking_id
            """),
            {"booking_id": booking_id},
        ).mappings().all()

        for slot in slot_rows:
            connection.execute(
                sa.text("""
                    UPDATE booking_time_slots
                    SET is_available = true
                    WHERE id = :slot_id
                """),
                {"slot_id": slot["time_slot_id"]},
            )

        connection.execute(
            sa.text("""
                DELETE FROM booking_slot_assignments
                WHERE booking_id = :booking_id
            """),
            {"booking_id": booking_id},
        )

    op.drop_table("booking_slot_assignment_backfill_log")
