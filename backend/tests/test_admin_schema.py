import pytest
from pydantic import ValidationError

from app.schemas import AdminOrderStatus


def test_admin_order_status_accepts_supported_fulfilment_stages():
    assert AdminOrderStatus(status="processing").status == "processing"
    assert AdminOrderStatus(status="dispatched").status == "dispatched"
    assert AdminOrderStatus(status="delivered").status == "delivered"


def test_admin_order_status_cannot_mark_payment_as_paid_or_cancel_order():
    with pytest.raises(ValidationError):
        AdminOrderStatus(status="paid")
    with pytest.raises(ValidationError):
        AdminOrderStatus(status="cancelled")
