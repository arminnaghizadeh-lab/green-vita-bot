from alembic import op
import sqlalchemy as sa

revision = "0018_admin_dashboard_preferences"
down_revision = "0017_inventory_warehouses"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_dashboard_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("widgets", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("admin_dashboard_preferences")
