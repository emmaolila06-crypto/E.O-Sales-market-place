"""Add managed collection points and order references."""
from alembic import op
import sqlalchemy as sa

revision = "0004_collection_points"
down_revision = "0003_commission_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("contact_phone", sa.String(length=40), nullable=True),
        sa.Column("opening_hours", sa.String(length=160), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_collection_points_name", "collection_points", ["name"])
    op.create_index("ix_collection_points_is_active", "collection_points", ["is_active"])
    op.add_column("orders", sa.Column("collection_point_id", sa.Integer(), nullable=True))
    op.create_index("ix_orders_collection_point_id", "orders", ["collection_point_id"])
    with op.batch_alter_table("orders") as batch_op:
        batch_op.create_foreign_key("fk_orders_collection_point_id_collection_points", "collection_points", ["collection_point_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("fk_orders_collection_point_id_collection_points", type_="foreignkey")
        batch_op.drop_column("collection_point_id")
    op.drop_index("ix_orders_collection_point_id", table_name="orders")
    op.drop_index("ix_collection_points_is_active", table_name="collection_points")
    op.drop_index("ix_collection_points_name", table_name="collection_points")
    op.drop_table("collection_points")
