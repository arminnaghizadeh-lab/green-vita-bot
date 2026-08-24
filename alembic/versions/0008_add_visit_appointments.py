"""add visit appointments scheduler

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visit_appointments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column(
            "status",
            sa.Enum(
                "scheduled",
                "confirmed",
                "in_progress",
                "completed",
                "cancelled",
                name="appointmentstatus",
            ),
            nullable=False,
            server_default="scheduled",
        ),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnoses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("diagnosis_id"),
    )

    op.create_index(
        "ix_visit_appointments_start_at",
        "visit_appointments",
        ["start_at"],
    )
    op.create_index(
        "ix_visit_appointments_blocked_until",
        "visit_appointments",
        ["blocked_until"],
    )
    op.create_index(
        "ix_visit_appointments_status_start",
        "visit_appointments",
        ["status", "start_at"],
    )

    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            ALTER TABLE visit_appointments
            ADD CONSTRAINT visit_appointments_no_overlap
            EXCLUDE USING gist (
                tstzrange(start_at, blocked_until, '[)')
                WITH &&
            )
            WHERE (status <> 'cancelled')
            """
        )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE visit_appointments DROP CONSTRAINT IF EXISTS visit_appointments_no_overlap"
        )

    op.drop_index("ix_visit_appointments_status_start", table_name="visit_appointments")
    op.drop_index("ix_visit_appointments_blocked_until", table_name="visit_appointments")
    op.drop_index("ix_visit_appointments_start_at", table_name="visit_appointments")
    op.drop_table("visit_appointments")

    if bind.dialect.name == "postgresql":
        sa.Enum(name="appointmentstatus").drop(bind, checkfirst=True)
