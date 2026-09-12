"""expand bookingstatus to match visit statuses

Revision ID: 7f4b2c91d8e3
Revises: 23a0b57946a5
Create Date: 2026-09-12
"""

from alembic import op


revision = "7f4b2c91d8e3"
down_revision = "23a0b57946a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TYPE bookingstatus
        ADD VALUE IF NOT EXISTS 'REVIEWING' BEFORE 'CONFIRMED'
    """)

    op.execute("""
        ALTER TYPE bookingstatus
        ADD VALUE IF NOT EXISTS 'SCHEDULED' BEFORE 'CONFIRMED'
    """)

    op.execute("""
        ALTER TYPE bookingstatus
        ADD VALUE IF NOT EXISTS 'IN_PROGRESS' BEFORE 'COMPLETED'
    """)


def downgrade() -> None:
    # PostgreSQL does not support removing individual enum values directly.
    pass
