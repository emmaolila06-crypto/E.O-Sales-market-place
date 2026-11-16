"""Add collection points, seller payouts and fulfilment accounting."""
from alembic import op
import sqlalchemy as sa

revision = "0002_operations"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("contact_phone", sa.String(40)),
        sa.Column("opening_hours", sa.String(160)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_collection_points_name", "collection_points", ["name"])
    op.create_index("ix_collection_points_is_active", "collection_points", ["is_active"])

    op.add_column("orders", sa.Column("collection_point_id", sa.Integer(), nullable=True))
    op.create_index("ix_orders_collection_point_id", "orders", ["collection_point_id"])
    op.create_foreign_key(
        "fk_orders_collection_point_id_collection_points",
        "orders", "collection_points", ["collection_point_id"], ["id"]
    )

    op.add_column("order_items", sa.Column("fulfilment_status", sa.String(30), nullable=False, server_default="pending"))
    op.add_column("order_items", sa.Column("delivery_tracking_code", sa.String(24), nullable=True))
    op.add_column("order_items", sa.Column("courier_name", sa.String(120), nullable=True))
    op.add_column("order_items", sa.Column("courier_phone", sa.String(40), nullable=True))
    op.add_column("order_items", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("order_items", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("order_items", sa.Column("commission_bps", sa.Integer(), nullable=False, server_default="1000"))
    op.add_column("order_items", sa.Column("platform_fee_ugx", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("order_items", sa.Column("seller_earning_ugx", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_order_items_fulfilment_status", "order_items", ["fulfilment_status"])
    op.create_index("ix_order_items_delivery_tracking_code", "order_items", ["delivery_tracking_code"], unique=True)

    op.create_table(
        "payout_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("seller_profiles.id"), nullable=False),
        sa.Column("amount_ugx", sa.Integer(), nullable=False),
        sa.Column("payout_method", sa.String(30), nullable=False),
        sa.Column("recipient_name", sa.String(160), nullable=False),
        sa.Column("payout_phone", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("review_note", sa.String(500), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_payout_requests_seller_id", "payout_requests", ["seller_id"])
    op.create_index("ix_payout_requests_status", "payout_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_payout_requests_status", table_name="payout_requests")
    op.drop_index("ix_payout_requests_seller_id", table_name="payout_requests")
    op.drop_table("payout_requests")

    op.drop_index("ix_order_items_delivery_tracking_code", table_name="order_items")
    op.drop_index("ix_order_items_fulfilment_status", table_name="order_items")
    for column in (
        "seller_earning_ugx", "platform_fee_ugx", "commission_bps",
        "delivered_at", "dispatched_at", "courier_phone", "courier_name",
        "delivery_tracking_code", "fulfilment_status",
    ):
        op.drop_column("order_items", column)

    op.drop_constraint(
        "fk_orders_collection_point_id_collection_points", "orders", type_="foreignkey"
    )
    op.drop_index("ix_orders_collection_point_id", table_name="orders")
    op.drop_column("orders", "collection_point_id")

    op.drop_index("ix_collection_points_is_active", table_name="collection_points")
    op.drop_index("ix_collection_points_name", table_name="collection_points")
    op.drop_table("collection_points")
