"""add manual customer address and description

Revision ID: 9c1d7e4b6a21
Revises: 7f4b2c91d8e3
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "9c1d7e4b6a21"
down_revision = "7f4b2c91d8e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "visit_appointments",
        sa.Column(
            "customer_address",
            sa.Text(),
            nullable=True,
        ),
    )

    op.add_column(
        "visit_appointments",
        sa.Column(
            "customer_description",
            sa.Text(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "visit_appointments",
        "customer_description",
    )

    op.drop_column(
        "visit_appointments",
        "customer_address",
    )
