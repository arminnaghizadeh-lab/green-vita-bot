"""add diagnoses table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    diagnosis_severity = sa.Enum(
        "none", "mild", "moderate", "severe", "unknown", name="diagnosisseverity"
    )

    op.create_table(
        "diagnoses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plant_id", sa.Integer(), sa.ForeignKey("plants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("telegram_file_id", sa.String(255), nullable=False),
        sa.Column("is_healthy", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("disease_name", sa.String(255), nullable=False, server_default="نامشخص"),
        sa.Column("severity", diagnosis_severity, nullable=False, server_default="unknown"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("symptoms", sa.Text(), nullable=True),
        sa.Column("treatment", sa.Text(), nullable=True),
        sa.Column("prevention", sa.Text(), nullable=True),
        sa.Column("ai_provider", sa.String(32), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_diagnoses_user_id", "diagnoses", ["user_id"])
    op.create_index("ix_diagnoses_plant_id", "diagnoses", ["plant_id"])


def downgrade() -> None:
    op.drop_table("diagnoses")
    sa.Enum(name="diagnosisseverity").drop(op.get_bind(), checkfirst=True)
