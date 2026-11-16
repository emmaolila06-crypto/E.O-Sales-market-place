from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    password: str = Field(min_length=10, max_length=128)
    language: str = Field(default="en", pattern="^(en|lg|sw)$")
    account_type: str = Field(default="customer", pattern="^(customer|seller)$")
    store_name: str | None = Field(default=None, min_length=2, max_length=160)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str | None
    role: str
    language: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str = ""
    category: str = Field(default="General", max_length=100)
    price_ugx: int = Field(gt=0)
    stock_quantity: int = Field(ge=0)
    image_url: str | None = Field(default=None, max_length=1000)


class ProductOut(BaseModel):
    id: int
    seller_id: int
    name: str
    description: str
    category: str
    price_ugx: int
    stock_quantity: int
    image_url: str | None
    model_config = ConfigDict(from_attributes=True)


class OrderLineInput(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=100)


class OrderCreate(BaseModel):
    items: list[OrderLineInput] = Field(min_length=1, max_length=50)
    payment_method: str = Field(pattern="^(mtn_momo|airtel_money|visa|mastercard|cash_on_delivery)$")
    fulfilment_method: str = Field(pattern="^(home_delivery|collection)$")
    delivery_address: str | None = Field(default=None, max_length=2000)
    collection_point: str | None = Field(default=None, max_length=255)
    collection_point_id: int | None = Field(default=None, gt=0)


class OrderItemOut(BaseModel):
    product_id: int
    seller_id: int
    product_name: str
    quantity: int
    unit_price_ugx: int
    line_total_ugx: int
    fulfilment_status: str
    delivery_tracking_code: str | None = None
    courier_name: str | None = None
    courier_phone: str | None = None
    dispatched_at: datetime | None = None
    delivered_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    status: str
    payment_status: str
    payment_method: str
    fulfilment_method: str
    delivery_address: str | None
    collection_point: str | None
    total_ugx: int
    items: list[OrderItemOut]
    model_config = ConfigDict(from_attributes=True)

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    price_ugx: int | None = Field(default=None, gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        if any(value is None for value in self.model_dump(exclude_unset=True).values()):
            raise ValueError("Product fields cannot be cleared with null; omit fields that should remain unchanged")
        return self


class AdminOrderStatus(BaseModel):
    status: str = Field(pattern="^(processing|dispatched|delivered)$")


class SellerFulfilmentUpdate(BaseModel):
    fulfilment_status: str = Field(pattern="^(processing|ready_for_collection|dispatched|delivered)$")
    courier_name: str | None = Field(default=None, max_length=120)
    courier_phone: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def validate_courier_details(self):
        if any(value is None for key, value in self.model_dump(exclude_unset=True).items() if key in {"courier_name", "courier_phone"}):
            raise ValueError("Courier details cannot be cleared with null")
        return self


class CollectionPointCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    address: str = Field(min_length=5, max_length=500)
    district: str = Field(default="", max_length=100)
    contact_phone: str | None = Field(default=None, max_length=40)
    opening_hours: str | None = Field(default=None, max_length=160)


class CollectionPointUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    address: str | None = Field(default=None, min_length=5, max_length=500)
    district: str | None = Field(default=None, max_length=100)
    contact_phone: str | None = Field(default=None, max_length=40)
    opening_hours: str | None = Field(default=None, max_length=160)
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        if any(value is None for value in self.model_dump(exclude_unset=True).values()):
            raise ValueError("Collection point fields cannot be cleared with null")
        return self
