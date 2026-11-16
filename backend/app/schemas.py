from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class OrderItemOut(BaseModel):
    product_id: int
    seller_id: int
    product_name: str
    quantity: int
    unit_price_ugx: int
    line_total_ugx: int
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
