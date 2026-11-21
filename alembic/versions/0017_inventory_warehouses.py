"""Create configurable inventory warehouses and preserve legacy codes."""

from alembic import op
import sqlalchemy as sa


revision = "0017_inventory_warehouses"
down_revision = "0016_invoice_customer_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_warehouses",
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("code", name="pk_inventory_warehouses"),
    )

    warehouse_table = sa.table(
        "inventory_warehouses",
        sa.column("code", sa.String(length=20)),
        sa.column("name", sa.String(length=100)),
        sa.column("is_active", sa.Boolean()),
    )

    op.bulk_insert(
        warehouse_table,
        [
            {"code": "main", "name": "انبار اصلی", "is_active": True},
            {"code": "quarantine", "name": "قرنطینه", "is_active": True},
        ],
    )

    op.create_index(
        "ix_inventory_warehouses_is_active",
        "inventory_warehouses",
        ["is_active"],
    )

    op.drop_constraint(
        "ck_inventory_movement_warehouse",
        "inventory_movements",
        type_="check",
    )

    op.create_foreign_key(
        "fk_inventory_movements_warehouse_inventory_warehouses",
        "inventory_movements",
        "inventory_warehouses",
        ["warehouse"],
        ["code"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    bind = op.get_bind()

    extra_movements = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM inventory_movements "
            "WHERE warehouse NOT IN ('main', 'quarantine')"
        )
    ).scalar_one()

    extra_warehouses = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM inventory_warehouses "
            "WHERE code NOT IN ('main', 'quarantine')"
        )
    ).scalar_one()

    if extra_movements or extra_warehouses:
        raise RuntimeError(
            "Downgrade refused: additional warehouses or their movements exist."
        )

    op.drop_constraint(
        "fk_inventory_movements_warehouse_inventory_warehouses",
        "inventory_movements",
        type_="foreignkey",
    )

    op.create_check_constraint(
        "ck_inventory_movement_warehouse",
        "inventory_movements",
        "warehouse IN ('main','quarantine')",
    )

    op.drop_index(
        "ix_inventory_warehouses_is_active",
        table_name="inventory_warehouses",
    )
    op.drop_table("inventory_warehouses")
