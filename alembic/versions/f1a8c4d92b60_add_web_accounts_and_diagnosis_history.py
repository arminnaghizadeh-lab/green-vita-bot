"""Add web accounts, daily diagnosis history, and password reset tokens."""

from alembic import op
import sqlalchemy as sa

revision = "f1a8c4d92b60"
down_revision = "9c1d7e4b6a21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "web_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", name="uq_web_accounts_user_id"),
    )
    op.create_index(
        "ix_web_accounts_phone_number",
        "web_accounts", ["phone_number"], unique=True,
    )

    op.create_table(
        "web_diagnosis_usages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(),
            sa.ForeignKey("web_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("plant_name", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("image_filename", sa.String(255), nullable=True),
        sa.Column("image_sha256", sa.String(64), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("ai_provider", sa.String(32), nullable=True),
        sa.Column(
            "status", sa.String(16), nullable=False,
            server_default=sa.text("'processing'"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "account_id", "usage_date",
            name="uq_web_diagnosis_account_day",
        ),
    )
    op.create_index(
        "ix_web_diagnosis_account_created",
        "web_diagnosis_usages", ["account_id", "created_at"],
    )

    op.create_table(
        "web_password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "account_id", sa.Integer(),
            sa.ForeignKey("web_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_web_password_reset_tokens_account_id",
        "web_password_reset_tokens", ["account_id"],
    )
    op.create_index(
        "ix_web_password_reset_tokens_token_hash",
        "web_password_reset_tokens", ["token_hash"], unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_web_password_reset_tokens_token_hash",
        table_name="web_password_reset_tokens",
    )
    op.drop_index(
        "ix_web_password_reset_tokens_account_id",
        table_name="web_password_reset_tokens",
    )
    op.drop_table("web_password_reset_tokens")
    op.drop_index(
        "ix_web_diagnosis_account_created",
        table_name="web_diagnosis_usages",
    )
    op.drop_table("web_diagnosis_usages")
    op.drop_index(
        "ix_web_accounts_phone_number",
        table_name="web_accounts",
    )
    op.drop_table("web_accounts")
