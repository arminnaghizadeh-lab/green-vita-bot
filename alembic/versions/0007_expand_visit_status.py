"""expand visit status enum

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-18

"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'reviewing'")
        op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'confirmed'")
        op.execute("ALTER TYPE visitstatus ADD VALUE IF NOT EXISTS 'in_progress'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly.
    pass
