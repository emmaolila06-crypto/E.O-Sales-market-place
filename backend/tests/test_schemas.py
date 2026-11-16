import pytest
from pydantic import ValidationError
from app.schemas import OrderCreate, ProductCreate, ProductUpdate, UserCreate


def test_user_language_is_restricted_to_supported_languages():
    user = UserCreate(email="buyer@example.com", full_name="Test Buyer",
                      password="long-enough-password", language="lg")
    assert user.language == "lg"
    with pytest.raises(ValidationError):
        UserCreate(email="buyer2@example.com", full_name="Test Buyer",
                   password="long-enough-password", language="fr")


def test_product_prices_must_be_positive_integer_ugx():
    assert ProductCreate(name="Rice", price_ugx=5000, stock_quantity=4).price_ugx == 5000
    with pytest.raises(ValidationError):
        ProductCreate(name="Rice", price_ugx=0, stock_quantity=4)


def test_product_update_supports_partial_changes():
    update = ProductUpdate(stock_quantity=7)
    assert update.model_dump(exclude_unset=True) == {"stock_quantity": 7}


def test_order_requires_at_least_one_item():
    with pytest.raises(ValidationError):
        OrderCreate(items=[], payment_method="mtn_momo",
                    fulfilment_method="home_delivery", delivery_address="Kampala")
