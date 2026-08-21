"""add plant_identifications table

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    difficulty_level = sa.Enum("easy", "medium", "hard", "unknown", name="difficultylevel")

    op.create_table(
        "plant_identifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_file_id", sa.String(255), nullable=False),
        sa.Column("persian_name", sa.String(255), nullable=False, server_default="نامشخص"),
        sa.Column("scientific_name", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("difficulty_level", difficulty_level, nullable=False, server_default="unknown"),
        sa.Column("light_requirement", sa.Text(), nullable=True),
        sa.Column("watering_schedule", sa.Text(), nullable=True),
        sa.Column("humidity", sa.Text(), nullable=True),
        sa.Column("temperature", sa.Text(), nullable=True),
        sa.Column("soil_mix", sa.Text(), nullable=True),
        sa.Column("fertilizer_recommendation", sa.Text(), nullable=True),
        sa.Column("potting_advice", sa.Text(), nullable=True),
        sa.Column("repotting_interval", sa.Text(), nullable=True),
        sa.Column("propagation_methods", sa.Text(), nullable=True),
        sa.Column("common_pests", sa.Text(), nullable=True),
        sa.Column("common_diseases", sa.Text(), nullable=True),
        sa.Column("toxicity_pets", sa.Text(), nullable=True),
        sa.Column("toxicity_humans", sa.Text(), nullable=True),
        sa.Column("preventive_care_tips", sa.Text(), nullable=True),
        sa.Column("ai_provider", sa.String(32), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column(
            "expert_visit_requested", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_plant_identifications_user_id", "plant_identifications", ["user_id"])


def downgrade() -> None:
    op.drop_table("plant_identifications")
    sa.Enum(name="difficultylevel").drop(op.get_bind(), checkfirst=True)
