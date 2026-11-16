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
