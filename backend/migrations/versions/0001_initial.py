"""Create initial marketplace tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("phone", sa.String(40)),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("language", sa.String(5), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table("seller_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("store_name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False))
    op.create_index("ix_seller_profiles_user_id", "seller_profiles", ["user_id"], unique=True)
    op.create_index("ix_seller_profiles_status", "seller_profiles", ["status"])

    op.create_table("products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("seller_profiles.id"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("price_ugx", sa.Integer(), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(1000)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    for column in ("seller_id", "name", "category", "is_active"):
        op.create_index(f"ix_products_{column}", "products", [column])

    op.create_table("orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payment_status", sa.String(30), nullable=False),
        sa.Column("payment_method", sa.String(30), nullable=False),
        sa.Column("fulfilment_method", sa.String(30), nullable=False),
        sa.Column("delivery_address", sa.Text()),
        sa.Column("collection_point", sa.String(255)),
        sa.Column("total_ugx", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])

    op.create_table("order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("seller_profiles.id"), nullable=False),
        sa.Column("product_name", sa.String(180), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_ugx", sa.Integer(), nullable=False),
        sa.Column("line_total_ugx", sa.Integer(), nullable=False))
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_seller_id", "order_items", ["seller_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_seller_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
    for column in ("is_active", "category", "name", "seller_id"):
        op.drop_index(f"ix_products_{column}", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_seller_profiles_status", table_name="seller_profiles")
    op.drop_index("ix_seller_profiles_user_id", table_name="seller_profiles")
    op.drop_table("seller_profiles")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
