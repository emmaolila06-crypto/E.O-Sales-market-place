"""Add seller payout request and review records."""
from alembic import op
import sqlalchemy as sa

revision = "0006_seller_payouts"
down_revision = "0005_delivery_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payout_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seller_id", sa.Integer(), sa.ForeignKey("seller_profiles.id"), nullable=False),
        sa.Column("amount_ugx", sa.Integer(), nullable=False),
        sa.Column("payout_method", sa.String(length=30), nullable=False),
        sa.Column("recipient_name", sa.String(length=160), nullable=False),
        sa.Column("payout_phone", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("review_note", sa.String(length=500), nullable=True),
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
