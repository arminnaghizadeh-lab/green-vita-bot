"""Add accounting chart of accounts, journal entries and ledger lines."""

import sqlalchemy as sa
from alembic import op


revision = "0014_accounting_ledgers"
down_revision = "0013_invoices"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "accounting_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("normal_balance", sa.String(10), nullable=False),
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("accounting_accounts.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("is_postable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("requires_party", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "account_type IN ('asset','liability','equity','revenue','expense')",
            name="ck_accounting_accounts_type",
        ),
        sa.CheckConstraint(
            "normal_balance IN ('debit','credit')",
            name="ck_accounting_accounts_normal_balance",
        ),
    )
    op.create_index(
        "ix_accounting_accounts_code",
        "accounting_accounts",
        ["code"],
        unique=False,
    )

    op.create_table(
        "accounting_journal_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="posted"),
        sa.Column("total_debit", sa.Numeric(18, 0), nullable=False),
        sa.Column("total_credit", sa.Numeric(18, 0), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "total_debit = total_credit AND total_debit > 0",
            name="ck_accounting_journal_balanced",
        ),
    )
    op.create_index(
        "ix_accounting_journal_entries_entry_date",
        "accounting_journal_entries",
        ["entry_date"],
    )

    op.create_table(
        "accounting_journal_lines",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "journal_id",
            sa.BigInteger(),
            sa.ForeignKey("accounting_journal_entries.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column(
            "account_id",
            sa.Integer(),
            sa.ForeignKey("accounting_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("debit", sa.Numeric(18, 0), nullable=False, server_default="0"),
        sa.Column("credit", sa.Numeric(18, 0), nullable=False, server_default="0"),
        sa.Column("party_type", sa.String(20), nullable=True),
        sa.Column("party_id", sa.BigInteger(), nullable=True),
        sa.Column("party_name", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("journal_id", "line_no", name="uq_accounting_journal_line_no"),
        sa.CheckConstraint(
            "debit >= 0 AND credit >= 0 "
            "AND ((debit > 0 AND credit = 0) "
            "OR (credit > 0 AND debit = 0))",
            name="ck_accounting_journal_line_one_side",
        ),
    )
    op.create_index(
        "ix_accounting_journal_lines_journal_id",
        "accounting_journal_lines",
        ["journal_id"],
    )
    op.create_index(
        "ix_accounting_journal_lines_account_id",
        "accounting_journal_lines",
        ["account_id"],
    )

    # Initial chart of accounts. Group accounts are not directly postable.
    rows = [
        ("1000", "دارایی‌ها", "asset", "debit", None, False, False),
        ("1100", "دارایی‌های جاری", "asset", "debit", "1000", False, False),
        ("1101", "صندوق", "asset", "debit", "1100", True, False),
        ("1102", "بانک", "asset", "debit", "1100", True, False),
        ("1103", "تنخواه‌گردان", "asset", "debit", "1100", True, False),
        ("1200", "حساب‌های دریافتنی", "asset", "debit", "1100", True, True),
        ("1300", "موجودی کالا", "asset", "debit", "1100", True, False),
        ("2000", "بدهی‌ها", "liability", "credit", None, False, False),
        ("2100", "بدهی‌های جاری", "liability", "credit", "2000", False, False),
        ("2101", "حساب‌های پرداختنی", "liability", "credit", "2100", True, True),
        ("3000", "حقوق مالکانه", "equity", "credit", None, False, False),
        ("3101", "سرمایه", "equity", "credit", "3000", True, False),
        ("3201", "برداشت", "equity", "debit", "3000", True, False),
        ("4000", "درآمدها", "revenue", "credit", None, False, False),
        ("4101", "درآمد فروش کالا", "revenue", "credit", "4000", True, False),
        ("4201", "درآمد خدمات", "revenue", "credit", "4000", True, False),
        ("5000", "بهای تمام‌شده", "expense", "debit", None, False, False),
        ("5101", "بهای تمام‌شده کالای فروش‌رفته", "expense", "debit", "5000", True, False),
        ("6000", "هزینه‌ها", "expense", "debit", None, False, False),
        ("6101", "هزینه‌های عمومی و اداری", "expense", "debit", "6000", True, False),
        ("6201", "هزینه رفت‌وآمد", "expense", "debit", "6000", True, False),
        ("6301", "هزینه تبلیغات", "expense", "debit", "6000", True, False),
        ("6401", "هزینه‌های بانکی", "expense", "debit", "6000", True, False),
    ]

    bind = op.get_bind()
    ids = {}

    for code, name, kind, normal, parent_code, postable, requires_party in rows:
        parent_id = ids.get(parent_code) if parent_code else None
        new_id = bind.execute(
            sa.text(
                """
                INSERT INTO accounting_accounts
                    (code, name, account_type, normal_balance, parent_id,
                     is_postable, requires_party, is_active)
                VALUES
                    (:code, :name, :kind, :normal, :parent_id,
                     :postable, :requires_party, true)
                RETURNING id
                """
            ),
            {
                "code": code,
                "name": name,
                "kind": kind,
                "normal": normal,
                "parent_id": parent_id,
                "postable": postable,
                "requires_party": requires_party,
            },
        ).scalar_one()
        ids[code] = new_id


def downgrade():
    op.drop_index("ix_accounting_journal_lines_account_id", table_name="accounting_journal_lines")
    op.drop_index("ix_accounting_journal_lines_journal_id", table_name="accounting_journal_lines")
    op.drop_table("accounting_journal_lines")
    op.drop_index("ix_accounting_journal_entries_entry_date", table_name="accounting_journal_entries")
    op.drop_table("accounting_journal_entries")
    op.drop_index("ix_accounting_accounts_code", table_name="accounting_accounts")
    op.drop_table("accounting_accounts")
