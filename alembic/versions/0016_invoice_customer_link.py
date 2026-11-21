"""Link invoice customers to web accounts and invoices to customers."""

from alembic import op
import sqlalchemy as sa


revision = "0016_invoice_customer_link"
down_revision = "0015_inventory_purchase_returns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A customer can be linked to at most one web account.
    # NULL allows existing and not-yet-verified customers to remain unlinked.
    op.add_column(
        "inv_customers",
        sa.Column("web_account_id", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_inv_customers_web_account_id_web_accounts",
        "inv_customers",
        "web_accounts",
        ["web_account_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_unique_constraint(
        "uq_inv_customers_web_account_id",
        "inv_customers",
        ["web_account_id"],
    )

    # Historical invoices keep their original JSON snapshot.
    # The nullable relational key is added separately.
    op.add_column(
        "inv_invoices",
        sa.Column("customer_id", sa.BigInteger(), nullable=True),
    )

    op.create_foreign_key(
        "fk_inv_invoices_customer_id_inv_customers",
        "inv_invoices",
        "inv_customers",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_index(
        "ix_inv_invoices_customer_id",
        "inv_invoices",
        ["customer_id"],
    )

    # Backfill only unambiguous exact normalized-name matches.
    # Ambiguous or unmatched invoices remain NULL for manual review.
    op.execute(
        """
        WITH candidates AS (
            SELECT
                i.id AS invoice_id,
                MIN(c.id) AS customer_id
            FROM inv_invoices AS i
            JOIN inv_customers AS c
              ON lower(trim(COALESCE(c.data->>'name', c.name)))
               = lower(trim(COALESCE(
                    i.data #>> '{cust,name}',
                    i.customer_name
                  )))
            GROUP BY i.id
            HAVING COUNT(c.id) = 1
        )
        UPDATE inv_invoices AS i
        SET customer_id = candidates.customer_id
        FROM candidates
        WHERE i.id = candidates.invoice_id
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inv_invoices_customer_id",
        table_name="inv_invoices",
    )

    op.drop_constraint(
        "fk_inv_invoices_customer_id_inv_customers",
        "inv_invoices",
        type_="foreignkey",
    )

    op.drop_column("inv_invoices", "customer_id")

    op.drop_constraint(
        "uq_inv_customers_web_account_id",
        "inv_customers",
        type_="unique",
    )

    op.drop_constraint(
        "fk_inv_customers_web_account_id_web_accounts",
        "inv_customers",
        type_="foreignkey",
    )

    op.drop_column("inv_customers", "web_account_id")
