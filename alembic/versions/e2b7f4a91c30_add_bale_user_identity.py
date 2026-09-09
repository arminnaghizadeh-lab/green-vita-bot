"""add Bale user identity

Revision ID: e2b7f4a91c30
Revises: d81c4e72b91a
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "e2b7f4a91c30"
down_revision: str | None = "d81c4e72b91a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )

    op.add_column(
        "users",
        sa.Column(
            "bale_id",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_users_bale_id",
        "users",
        ["bale_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_users_bale_id",
        table_name="users",
    )

    op.drop_column(
        "users",
        "bale_id",
    )

    bind = op.get_bind()
    remaining_nulls = bind.execute(
        sa.text("SELECT COUNT(*) FROM users WHERE telegram_id IS NULL")
    ).scalar_one()

    if remaining_nulls:
        raise RuntimeError(
            "Cannot downgrade: users with NULL telegram_id still exist."
        )

    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
