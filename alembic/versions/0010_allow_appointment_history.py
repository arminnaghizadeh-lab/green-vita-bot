"""allow multiple appointment history rows per diagnosis

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-25
"""

from alembic import op


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "visit_appointments_diagnosis_id_key",
        "visit_appointments",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "visit_appointments_diagnosis_id_key",
        "visit_appointments",
        ["diagnosis_id"],
    )
