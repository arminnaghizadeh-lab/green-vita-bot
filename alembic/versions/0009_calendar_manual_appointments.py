"""allow manual calendar appointments

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    inspector = sa.inspect(bind)

    # Find the existing FK created by 0008 without assuming
    # PostgreSQL's generated constraint name.
    foreign_keys = inspector.get_foreign_keys(
        "visit_appointments"
    )

    for fk in foreign_keys:
        if fk.get("constrained_columns") == ["diagnosis_id"]:
            if fk.get("name"):
                op.drop_constraint(
                    fk["name"],
                    "visit_appointments",
                    type_="foreignkey",
                )
            break

    # Manual appointments do not have a diagnosis/request.
    op.alter_column(
        "visit_appointments",
        "diagnosis_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Existing diagnosis appointments must still be protected,
    # while deleting a diagnosis must not delete a manual appointment.
    op.create_foreign_key(
        "fk_visit_appointments_diagnosis_id",
        "visit_appointments",
        "diagnoses",
        ["diagnosis_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "visit_appointments",
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default="bot",
        ),
    )

    op.add_column(
        "visit_appointments",
        sa.Column(
            "customer_name",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.add_column(
        "visit_appointments",
        sa.Column(
            "customer_phone",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.add_column(
        "visit_appointments",
        sa.Column(
            "customer_plant",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "visit_appointments",
        "customer_plant",
    )

    op.drop_column(
        "visit_appointments",
        "customer_phone",
    )

    op.drop_column(
        "visit_appointments",
        "customer_name",
    )

    op.drop_column(
        "visit_appointments",
        "source",
    )

    op.drop_constraint(
        "fk_visit_appointments_diagnosis_id",
        "visit_appointments",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_visit_appointments_diagnosis_id",
        "visit_appointments",
        "diagnoses",
        ["diagnosis_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.alter_column(
        "visit_appointments",
        "diagnosis_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
