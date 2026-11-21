"""Add invoice tables (inv_customers, inv_products, inv_invoices)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013_invoices"
down_revision = "f1a8c4d92b60"
branch_labels = None
depends_on = None


def _common():
    return [
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("data", JSONB, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade():
    for table_name in ("inv_customers", "inv_products"):
        op.create_table(
            table_name,
            *_common(),
            sa.Column("name", sa.String(200), nullable=False),
        )
        op.create_index(
            f"ix_{table_name}_name", table_name, ["name"]
        )

    op.create_table(
        "inv_invoices",
        *_common(),
        sa.Column("no", sa.String(32), nullable=False, unique=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=False),
        sa.Column(
            "date_text", sa.String(16), nullable=False, server_default=""
        ),
        sa.Column("payable", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_inv_invoices_status", "inv_invoices", ["status"])
    op.create_index(
        "ix_inv_invoices_customer_name",
        "inv_invoices",
        ["customer_name"],
    )


def downgrade():
    op.drop_table("inv_invoices")
    op.drop_table("inv_products")
    op.drop_table("inv_customers")
