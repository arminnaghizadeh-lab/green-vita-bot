"""Add inventory documents, purchase/return lines and stock movements."""

import sqlalchemy as sa
from alembic import op


revision = "0015_inventory_purchase_returns"
down_revision = "0014_accounting_ledgers"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_documents",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("document_no", sa.String(40), nullable=False),
        sa.Column("document_type", sa.String(24), nullable=False),
        sa.Column("document_date", sa.Date(), nullable=False),
        sa.Column("party_name", sa.String(200), nullable=True),
        sa.Column(
            "reference_invoice_id",
            sa.BigInteger(),
            sa.ForeignKey("inv_invoices.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("reference_invoice_no", sa.String(32), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "total_amount",
            sa.Numeric(18, 0),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="posted",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("document_no", name="uq_inventory_documents_no"),
        sa.CheckConstraint(
            "document_type IN ('purchase','sales_return','adjustment')",
            name="ck_inventory_document_type",
        ),
        sa.CheckConstraint(
            "status IN ('posted','void')",
            name="ck_inventory_document_status",
        ),
    )
    op.create_index(
        "ix_inventory_documents_type_date",
        "inventory_documents",
        ["document_type", "document_date"],
    )
    op.create_index(
        "ix_inventory_documents_reference_invoice",
        "inventory_documents",
        ["reference_invoice_id"],
    )

    op.create_table(
        "inventory_document_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            sa.BigInteger(),
            sa.ForeignKey("inventory_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("reference_line_no", sa.Integer(), nullable=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("inv_products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False, server_default=""),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column(
            "unit_price", sa.Numeric(18, 3), nullable=False, server_default="0"
        ),
        sa.Column(
            "unit_cost", sa.Numeric(18, 0), nullable=False, server_default="0"
        ),
        sa.Column(
            "line_total", sa.Numeric(18, 0), nullable=False, server_default="0"
        ),
        sa.Column("condition", sa.String(20), nullable=True),
        sa.UniqueConstraint(
            "document_id",
            "line_no",
            name="uq_inventory_document_line_no",
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_inventory_document_line_quantity",
        ),
    )
    op.create_index(
        "ix_inventory_document_lines_document",
        "inventory_document_lines",
        ["document_id"],
    )
    op.create_index(
        "ix_inventory_document_lines_product",
        "inventory_document_lines",
        ["product_id"],
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("inv_products.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("movement_date", sa.Date(), nullable=False),
        sa.Column(
            "warehouse",
            sa.String(20),
            nullable=False,
            server_default="main",
        ),
        sa.Column("quantity_delta", sa.Numeric(18, 3), nullable=False),
        sa.Column(
            "unit_cost", sa.Numeric(18, 0), nullable=False, server_default="0"
        ),
        sa.Column("source_type", sa.String(24), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("source_line", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "source_line",
            "warehouse",
            name="uq_inventory_movement_source_line",
        ),
        sa.CheckConstraint(
            "warehouse IN ('main','quarantine')",
            name="ck_inventory_movement_warehouse",
        ),
        sa.CheckConstraint(
            "quantity_delta <> 0",
            name="ck_inventory_movement_nonzero",
        ),
    )
    op.create_index(
        "ix_inventory_movements_product_date",
        "inventory_movements",
        ["product_id", "movement_date"],
    )
    op.create_index(
        "ix_inventory_movements_source",
        "inventory_movements",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_inventory_movements_product_warehouse",
        "inventory_movements",
        ["product_id", "warehouse"],
    )


def downgrade():
    op.drop_index(
        "ix_inventory_movements_product_warehouse",
        table_name="inventory_movements",
    )
    op.drop_index(
        "ix_inventory_movements_source",
        table_name="inventory_movements",
    )
    op.drop_index(
        "ix_inventory_movements_product_date",
        table_name="inventory_movements",
    )
    op.drop_table("inventory_movements")

    op.drop_index(
        "ix_inventory_document_lines_product",
        table_name="inventory_document_lines",
    )
    op.drop_index(
        "ix_inventory_document_lines_document",
        table_name="inventory_document_lines",
    )
    op.drop_table("inventory_document_lines")

    op.drop_index(
        "ix_inventory_documents_reference_invoice",
        table_name="inventory_documents",
    )
    op.drop_index(
        "ix_inventory_documents_type_date",
        table_name="inventory_documents",
    )
    op.drop_table("inventory_documents")
