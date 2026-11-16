"""Add commission snapshots to order items."""
from alembic import op
import sqlalchemy as sa

revision = "0003_commission_snapshot"
down_revision = "0002_item_fulfilment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("commission_bps", sa.Integer(), nullable=False, server_default="1000"))
    op.add_column("order_items", sa.Column("platform_fee_ugx", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("seller_earning_ugx", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("order_items", "seller_earning_ugx")
    op.drop_column("order_items", "platform_fee_ugx")
    op.drop_column("order_items", "commission_bps")
