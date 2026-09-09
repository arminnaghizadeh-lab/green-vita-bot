"""add unified visit queue sources

Revision ID: 23a0b57946a5
Revises: e2b7f4a91c30
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "23a0b57946a5"
down_revision: str | None = "e2b7f4a91c30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diagnoses",
        sa.Column(
            "expert_visit_source",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_diagnoses_expert_visit_source",
        "diagnoses",
        ["expert_visit_source"],
        unique=False,
    )

    op.add_column(
        "plant_identifications",
        sa.Column(
            "expert_visit_source",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_plant_identifications_expert_visit_source",
        "plant_identifications",
        ["expert_visit_source"],
        unique=False,
    )

    op.add_column(
        "visit_appointments",
        sa.Column(
            "identification_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_visit_appointments_identification_id",
        "visit_appointments",
        ["identification_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_visit_appointments_identification_id",
        "visit_appointments",
        "plant_identifications",
        ["identification_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_visit_appointments_identification_id",
        "visit_appointments",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_visit_appointments_identification_id",
        table_name="visit_appointments",
    )

    op.drop_column(
        "visit_appointments",
        "identification_id",
    )

    op.drop_index(
        "ix_plant_identifications_expert_visit_source",
        table_name="plant_identifications",
    )

    op.drop_column(
        "plant_identifications",
        "expert_visit_source",
    )

    op.drop_index(
        "ix_diagnoses_expert_visit_source",
        table_name="diagnoses",
    )

    op.drop_column(
        "diagnoses",
        "expert_visit_source",
    )
