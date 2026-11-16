from contextlib import asynccontextmanager

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from . import models, schemas
from .config import settings
from .database import Base, engine, get_db
from .security import create_access_token, decode_access_token, hash_password, verify_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all is convenient for local setup. Use versioned migrations in production.
    if settings.environment.lower() == "production" and len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters in production")
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired login token")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise unauthorized
    user = db.get(models.User, user_id)
    if not user or not user.is_active:
        raise unauthorized
    return user


def require_role(*roles: str):
    def checker(user: models.User = Depends(current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        return user
    return checker


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(models.User).where(models.User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if payload.account_type == "seller" and not payload.store_name:
        raise HTTPException(status_code=422, detail="store_name is required for seller registration")
    user = models.User(
        email=email,
        full_name=payload.full_name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.account_type,
        language=payload.language,
    )
    db.add(user)
    try:
        db.flush()
        if payload.account_type == "seller":
            db.add(models.SellerProfile(user_id=user.id, store_name=payload.store_name or "", status="pending"))
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    return user


@app.post("/auth/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginInput, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(current_user)):
    return user


@app.get("/seller/me")
def seller_me(user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
    profile = db.scalar(select(models.SellerProfile).where(models.SellerProfile.user_id == user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    return {"id": profile.id, "store_name": profile.store_name, "status": profile.status, "description": profile.description}


@app.get("/products", response_model=list[schemas.ProductOut])
def list_products(category: str | None = None, search: str | None = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 100))
    query = select(models.Product).where(models.Product.is_active.is_(True), models.Product.stock_quantity > 0)
    if category:
        query = query.where(models.Product.category == category)
    if search:
        query = query.where(models.Product.name.ilike(f"%{search.strip()}%"))
    return db.scalars(query.order_by(models.Product.created_at.desc()).offset(offset).limit(limit)).all()


@app.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(payload: schemas.ProductUpdate, user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
    profile = db.scalar(select(models.SellerProfile).where(models.SellerProfile.user_id == user.id))
    if not profile or profile.status != "approved":
        raise HTTPException(status_code=403, detail="Your seller account must be approved before listing products")
    product = models.Product(seller_id=profile.id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductCreate, user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
    profile = db.scalar(select(models.SellerProfile).where(models.SellerProfile.user_id == user.id))
    product = db.get(models.Product, product_id)
    if not profile or profile.status != "approved" or not product or product.seller_id != profile.id:
        raise HTTPException(status_code=404, detail="Product not found or not editable")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@app.post("/orders", response_model=schemas.OrderOut, status_code=201)
def create_order(payload: schemas.OrderCreate, user: models.User = Depends(require_role("customer")), db: Session = Depends(get_db)):
    if payload.fulfilment_method == "home_delivery" and not payload.delivery_address:
        raise HTTPException(status_code=422, detail="delivery_address is required for home delivery")
    if payload.fulfilment_method == "collection" and not payload.collection_point:
        raise HTTPException(status_code=422, detail="collection_point is required for collection")
    quantities: dict[int, int] = {}
    for line in payload.items:
        quantities[line.product_id] = quantities.get(line.product_id, 0) + line.quantity
    order = models.Order(
        customer_id=user.id,
        payment_method=payload.payment_method,
        fulfilment_method=payload.fulfilment_method,
        delivery_address=payload.delivery_address if payload.fulfilment_method == "home_delivery" else None,
        collection_point=payload.collection_point if payload.fulfilment_method == "collection" else None,
        payment_status="unpaid",
        status="awaiting_payment",
    )
    total = 0
    try:
        db.add(order)
        db.flush()
        for product_id, quantity in quantities.items():
            product = db.scalar(select(models.Product).where(models.Product.id == product_id, models.Product.is_active.is_(True)))
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {product_id} is unavailable")
            result = db.execute(
                update(models.Product)
                .where(models.Product.id == product_id, models.Product.stock_quantity >= quantity, models.Product.is_active.is_(True))
                .values(stock_quantity=models.Product.stock_quantity - quantity)
            )
            if result.rowcount != 1:
                raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")
            line_total = product.price_ugx * quantity
            total += line_total
            db.add(models.OrderItem(
                order_id=order.id,
                product_id=product.id,
                seller_id=product.seller_id,
                product_name=product.name,
                quantity=quantity,
                unit_price_ugx=product.price_ugx,
                line_total_ugx=line_total,
            ))
        order.total_ugx = total
        db.commit()
    except Exception:
        db.rollback()
        raise
    saved = db.scalar(select(models.Order).options(selectinload(models.Order.items)).where(models.Order.id == order.id))
    return saved


@app.get("/orders/my", response_model=list[schemas.OrderOut])
def my_orders(user: models.User = Depends(require_role("customer")), db: Session = Depends(get_db)):
    return db.scalars(
        select(models.Order).options(selectinload(models.Order.items))
        .where(models.Order.customer_id == user.id)
        .order_by(models.Order.created_at.desc())
    ).all()


@app.get("/seller/orders")
def seller_orders(user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
    profile = db.scalar(select(models.SellerProfile).where(models.SellerProfile.user_id == user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    rows = db.execute(
        select(models.OrderItem, models.Order)
        .join(models.Order, models.Order.id == models.OrderItem.order_id)
        .where(models.OrderItem.seller_id == profile.id)
        .order_by(models.Order.created_at.desc())
    ).all()
    return [
        {
            "order_id": order.id,
            "order_status": order.status,
            "payment_status": order.payment_status,
            "created_at": order.created_at,
            "item": {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price_ugx": item.unit_price_ugx,
                "line_total_ugx": item.line_total_ugx,
            },
        }
        for item, order in rows
    ]


@app.get("/admin/sellers")
def pending_sellers(user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    profiles = db.scalars(select(models.SellerProfile).where(models.SellerProfile.status == "pending")).all()
    return [{"id": p.id, "user_id": p.user_id, "store_name": p.store_name, "status": p.status} for p in profiles]


@app.post("/admin/sellers/{seller_id}/approve")
def approve_seller(seller_id: int, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    profile = db.get(models.SellerProfile, seller_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    profile.status = "approved"
    db.commit()
    return {"id": profile.id, "status": profile.status}


@app.post("/admin/sellers/{seller_id}/reject")
def reject_seller(seller_id: int, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    profile = db.get(models.SellerProfile, seller_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    profile.status = "rejected"
    db.commit()
    return {"id": profile.id, "status": profile.status}
