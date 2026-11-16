"""Add seller-specific fulfilment status to order items."""
from alembic import op
import sqlalchemy as sa

revision = "0002_item_fulfilment"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("fulfilment_status", sa.String(30), nullable=False, server_default="pending"),
    )
    op.create_index("ix_order_items_fulfilment_status", "order_items", ["fulfilment_status"])


def downgrade() -> None:
    op.drop_index("ix_order_items_fulfilment_status", table_name="order_items")
    op.drop_column("order_items", "fulfilment_status")
