"""Add seller dispatch and customer delivery tracking details."""
from alembic import op
import sqlalchemy as sa

revision = "0005_delivery_tracking"
down_revision = "0004_collection_points"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("order_items", sa.Column("delivery_tracking_code", sa.String(length=24), nullable=True))
    op.add_column("order_items", sa.Column("courier_name", sa.String(length=120), nullable=True))
    op.add_column("order_items", sa.Column("courier_phone", sa.String(length=40), nullable=True))
    op.add_column("order_items", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("order_items", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_order_items_delivery_tracking_code", "order_items", ["delivery_tracking_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_order_items_delivery_tracking_code", table_name="order_items")
    op.drop_column("order_items", "delivered_at")
    op.drop_column("order_items", "dispatched_at")
    op.drop_column("order_items", "courier_phone")
    op.drop_column("order_items", "courier_name")
    op.drop_column("order_items", "delivery_tracking_code")
