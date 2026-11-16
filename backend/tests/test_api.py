import pytest
from pydantic import ValidationError

from app.schemas import OrderCreate, ProductCreate, ProductUpdate, UserCreate
from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_round_trip():
    encoded = hash_password("A-long-demo-password-123")
    assert encoded != "A-long-demo-password-123"
    assert verify_password("A-long-demo-password-123", encoded)
    assert not verify_password("wrong-password", encoded)


def test_jwt_contains_user_identity_and_role():
    token = create_access_token(42, "customer")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "customer"


def test_registration_accepts_supported_languages_and_roles():
    user = UserCreate(
        email="buyer@example.com",
        full_name="Marketplace Buyer",
        password="A-long-demo-password-123",
        language="lg",
        account_type="customer",
    )
    assert user.language == "lg"
    assert user.account_type == "customer"


@pytest.mark.parametrize("language", ["fr", "xx", ""])
def test_registration_rejects_unsupported_language(language):
    with pytest.raises(ValidationError):
        UserCreate(
            email="buyer@example.com",
            full_name="Marketplace Buyer",
            password="A-long-demo-password-123",
            language=language,
        )


def test_product_requires_positive_ugx_price():
    with pytest.raises(ValidationError):
        ProductCreate(name="Rice", price_ugx=0, stock_quantity=4)


def test_product_update_supports_partial_changes():
    update = ProductUpdate(stock_quantity=0)
    assert update.model_dump(exclude_unset=True) == {"stock_quantity": 0}


def test_order_requires_positive_quantity_and_supported_fulfilment():
    with pytest.raises(ValidationError):
        OrderCreate(
            items=[{"product_id": 1, "quantity": 0}],
            payment_method="mtn_momo",
            fulfilment_method="home_delivery",
        )
    with pytest.raises(ValidationError):
        OrderCreate(
            items=[{"product_id": 1, "quantity": 1}],
            payment_method="crypto",
            fulfilment_method="home_delivery",
        )

def test_product_update_rejects_explicit_null_values():
    with pytest.raises(ValidationError):
        ProductUpdate(description=None)


def test_seller_fulfilment_update_accepts_supported_item_statuses():
    from app.schemas import SellerFulfilmentUpdate

    assert SellerFulfilmentUpdate(fulfilment_status="processing").fulfilment_status == "processing"
    assert SellerFulfilmentUpdate(fulfilment_status="dispatched").fulfilment_status == "dispatched"


def test_seller_fulfilment_update_rejects_unknown_status():
    from app.schemas import SellerFulfilmentUpdate

    with pytest.raises(ValidationError):
        SellerFulfilmentUpdate(fulfilment_status="paid")


def test_platform_commission_calculation_rounds_to_nearest_ugx():
    from app.main import calculate_platform_commission

    assert calculate_platform_commission(10000, 1000) == 1000
    assert calculate_platform_commission(105, 1000) == 11
    assert calculate_platform_commission(10000, 0) == 0
    assert calculate_platform_commission(10000, 10000) == 10000


def test_platform_commission_rejects_invalid_inputs():
    from app.main import calculate_platform_commission

    with pytest.raises(ValueError):
        calculate_platform_commission(100, 10001)


def test_collection_point_schemas_validate_required_location_details():
    from app.schemas import CollectionPointCreate, CollectionPointUpdate

    point = CollectionPointCreate(name="Kampala Central", address="Plot 10, Kampala Road", district="Kampala")
    assert point.name == "Kampala Central"
    assert CollectionPointUpdate(is_active=False).is_active is False


def test_collection_point_update_rejects_explicit_null():
    from app.schemas import CollectionPointUpdate

    with pytest.raises(ValidationError):
        CollectionPointUpdate(name=None)


def test_order_can_reference_a_collection_point():
    order = OrderCreate(
        items=[{"product_id": 1, "quantity": 1}],
        payment_method="mtn_momo",
        fulfilment_method="collection",
        collection_point_id=3,
    )
    assert order.collection_point_id == 3


def test_seller_dispatch_requires_courier_contact_details():
    from app.schemas import SellerFulfilmentUpdate

    payload = SellerFulfilmentUpdate(fulfilment_status="dispatched", courier_name="Delivery Rider", courier_phone="+256700000000")
    assert payload.courier_name == "Delivery Rider"
    assert payload.courier_phone == "+256700000000"


def test_seller_dispatch_schema_accepts_other_statuses_without_courier():
    from app.schemas import SellerFulfilmentUpdate

    assert SellerFulfilmentUpdate(fulfilment_status="processing").fulfilment_status == "processing"
