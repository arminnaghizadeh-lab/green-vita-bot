"""add smart bio click tracking

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "smart_bio_clicks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("referer", sa.Text(), nullable=True),
        sa.Column("source_path", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_smart_bio_clicks_channel",
        "smart_bio_clicks",
        ["channel"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_smart_bio_clicks_channel",
        table_name="smart_bio_clicks",
    )

    op.drop_table("smart_bio_clicks")
