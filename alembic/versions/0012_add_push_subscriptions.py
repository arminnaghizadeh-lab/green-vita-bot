"""add push subscriptions

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.String(length=512), nullable=False),
        sa.Column("auth", sa.String(length=512), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )

    op.create_index(
        "ix_push_subscriptions_endpoint",
        "push_subscriptions",
        ["endpoint"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_push_subscriptions_endpoint",
        table_name="push_subscriptions",
    )
    op.drop_table("push_subscriptions")
