from contextlib import asynccontextmanager

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
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
    if settings.jwt_expire_minutes <= 0:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be greater than zero")
    if not 0 <= settings.marketplace_commission_percent <= 100:
        raise RuntimeError("MARKETPLACE_COMMISSION_PERCENT must be between 0 and 100")
    if settings.environment.lower() == "production":
        if len(settings.jwt_secret) < 32 or settings.jwt_secret == "replace-this-development-secret":
            raise RuntimeError("Set a unique JWT_SECRET of at least 32 characters in production")
        if "*" in settings.allowed_origins:
            raise RuntimeError("Wildcard CORS origins are not allowed in production when credentials are enabled")
        if not settings.allowed_origins:
            raise RuntimeError("Set explicit CORS_ORIGINS for the production frontend")
    if settings.environment.lower() == "development":
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
    query = select(models.Product).join(models.SellerProfile, models.SellerProfile.id == models.Product.seller_id).where(models.Product.is_active.is_(True), models.Product.stock_quantity > 0, models.SellerProfile.status == "approved")
    if category:
        query = query.where(models.Product.category == category)
    if search:
        query = query.where(models.Product.name.ilike(f"%{search.strip()}%"))
    return db.scalars(query.order_by(models.Product.created_at.desc()).offset(offset).limit(limit)).all()


@app.post("/products", response_model=schemas.ProductOut, status_code=201)
def create_product(payload: schemas.ProductCreate, user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
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
    product = db.scalar(
        select(models.Product)
        .join(models.SellerProfile, models.SellerProfile.id == models.Product.seller_id)
        .where(
            models.Product.id == product_id,
            models.Product.is_active.is_(True),
            models.SellerProfile.status == "approved",
        )
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.patch("/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, payload: schemas.ProductUpdate, user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
    profile = db.scalar(select(models.SellerProfile).where(models.SellerProfile.user_id == user.id))
    product = db.get(models.Product, product_id)
    if not profile or profile.status != "approved" or not product or product.seller_id != profile.id:
        raise HTTPException(status_code=404, detail="Product not found or not editable")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def calculate_platform_commission(line_total_ugx: int, commission_bps: int) -> int:
    if line_total_ugx < 0 or not 0 <= commission_bps <= 10000:
        raise ValueError("Invalid commission calculation inputs")
    return (line_total_ugx * commission_bps + 5000) // 10000


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
            commission_bps = int(round(settings.marketplace_commission_percent * 100))
            if not 0 <= commission_bps <= 10000:
                raise HTTPException(status_code=500, detail="Marketplace commission configuration must be between 0 and 100 percent")
            platform_fee = calculate_platform_commission(line_total, commission_bps)
            total += line_total
            db.add(models.OrderItem(
                order_id=order.id,
                product_id=product.id,
                seller_id=product.seller_id,
                product_name=product.name,
                quantity=quantity,
                unit_price_ugx=product.price_ugx,
                line_total_ugx=line_total,
                commission_bps=commission_bps,
                platform_fee_ugx=platform_fee,
                seller_earning_ugx=line_total - platform_fee,
            ))
        order.total_ugx = total
        db.commit()
    except Exception:
        db.rollback()
        raise
    saved = db.scalar(select(models.Order).options(selectinload(models.Order.items)).where(models.Order.id == order.id))
    return saved


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: int, user: models.User = Depends(require_role("customer")), db: Session = Depends(get_db)):
    order = db.scalar(
        select(models.Order)
        .options(selectinload(models.Order.items))
        .where(models.Order.id == order_id, models.Order.customer_id == user.id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    try:
        # Conditional update makes cancellation idempotent under concurrent requests.
        changed = db.execute(
            update(models.Order)
            .where(
                models.Order.id == order_id,
                models.Order.customer_id == user.id,
                models.Order.payment_status == "unpaid",
                models.Order.status == "awaiting_payment",
            )
            .values(status="cancelled", payment_status="cancelled")
        )
        if changed.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail="Only unpaid orders awaiting payment can be cancelled. Paid or already-cancelled orders cannot be cancelled here.",
            )
        for item in order.items:
            db.execute(
                update(models.Product)
                .where(models.Product.id == item.product_id)
                .values(stock_quantity=models.Product.stock_quantity + item.quantity)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"id": order.id, "status": "cancelled", "payment_status": "cancelled"}


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
                "item_id": item.id,
                "fulfilment_status": item.fulfilment_status,
                "fulfilment_method": order.fulfilment_method,
            },
        }
        for item, order in rows
    ]


@app.patch("/seller/order-items/{item_id}/status")
def update_seller_order_item_status(item_id: int, payload: schemas.SellerFulfilmentUpdate, user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
    profile = db.scalar(select(models.SellerProfile).where(models.SellerProfile.user_id == user.id))
    if not profile or profile.status != "approved":
        raise HTTPException(status_code=403, detail="An approved seller account is required")
    item = db.get(models.OrderItem, item_id)
    if not item or item.seller_id != profile.id:
        raise HTTPException(status_code=404, detail="Order item not found")
    order = db.get(models.Order, item.order_id)
    if not order or order.payment_status != "paid":
        raise HTTPException(status_code=409, detail="Order items can only be processed after payment is confirmed")
    allowed = {
        "pending": {"processing"},
        "processing": {"ready_for_collection", "dispatched"},
        "ready_for_collection": {"delivered"},
        "dispatched": {"delivered"},
        "delivered": set(),
    }
    target = payload.fulfilment_status
    if target not in allowed.get(item.fulfilment_status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot move item from {item.fulfilment_status} to {target}")
    if target == "ready_for_collection" and order.fulfilment_method != "collection":
        raise HTTPException(status_code=409, detail="Ready for collection applies only to collection orders")
    if target == "dispatched" and order.fulfilment_method != "home_delivery":
        raise HTTPException(status_code=409, detail="Dispatch applies only to home-delivery orders")
    item.fulfilment_status = target
    db.commit()
    return {"item_id": item.id, "fulfilment_status": item.fulfilment_status}

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
    # Hide all existing listings immediately when a seller is rejected.
    db.execute(
        update(models.Product)
        .where(models.Product.seller_id == profile.id)
        .values(is_active=False)
    )
    db.commit()
    return {"id": profile.id, "status": profile.status, "products_deactivated": True}


@app.get("/seller/earnings")
def seller_earnings(user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
    from sqlalchemy import func
    profile = db.scalar(select(models.SellerProfile).where(models.SellerProfile.user_id == user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    paid = models.Order.payment_status == "paid"
    base = select(
        func.coalesce(func.sum(models.OrderItem.seller_earning_ugx), 0),
        func.coalesce(func.sum(models.OrderItem.platform_fee_ugx), 0),
        func.count(models.OrderItem.id),
    ).join(models.Order, models.Order.id == models.OrderItem.order_id).where(
        models.OrderItem.seller_id == profile.id, paid, models.Order.status != "cancelled"
    )
    earned, commission, lines = db.execute(base).one()
    return {"seller_id": profile.id, "paid_order_lines": lines, "gross_sales_ugx": int(earned + commission),
            "platform_commission_ugx": int(commission), "net_earnings_ugx": int(earned),
            "currency": "UGX", "payouts_enabled": False}


@app.get("/admin/finance/report")
def admin_finance_report(user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    from sqlalchemy import func
    paid = models.Order.payment_status == "paid"
    totals = db.execute(select(
        func.coalesce(func.sum(models.OrderItem.line_total_ugx), 0),
        func.coalesce(func.sum(models.OrderItem.platform_fee_ugx), 0),
        func.coalesce(func.sum(models.OrderItem.seller_earning_ugx), 0),
        func.count(models.OrderItem.id),
    ).join(models.Order, models.Order.id == models.OrderItem.order_id).where(paid, models.Order.status != "cancelled")).one()
    rows = db.execute(select(
        models.SellerProfile.id, models.SellerProfile.store_name,
        func.coalesce(func.sum(models.OrderItem.line_total_ugx), 0),
        func.coalesce(func.sum(models.OrderItem.platform_fee_ugx), 0),
        func.coalesce(func.sum(models.OrderItem.seller_earning_ugx), 0),
    ).join(models.OrderItem, models.OrderItem.seller_id == models.SellerProfile.id)
     .join(models.Order, models.Order.id == models.OrderItem.order_id)
     .where(paid, models.Order.status != "cancelled")
     .group_by(models.SellerProfile.id, models.SellerProfile.store_name)
     .order_by(models.SellerProfile.store_name)).all()
    return {"paid_gross_sales_ugx": int(totals[0]), "platform_commission_ugx": int(totals[1]),
            "seller_net_earnings_ugx": int(totals[2]), "paid_order_lines": int(totals[3]),
            "currency": "UGX", "payouts_enabled": False,
            "sellers": [{"seller_id": r[0], "store_name": r[1], "gross_sales_ugx": int(r[2]),
                        "platform_commission_ugx": int(r[3]), "net_earnings_ugx": int(r[4])} for r in rows]}

@app.get("/admin/overview")
def admin_overview(user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    from sqlalchemy import func

    total_customers = db.scalar(select(func.count(models.User.id)).where(models.User.role == "customer")) or 0
    total_sellers = db.scalar(select(func.count(models.SellerProfile.id))) or 0
    pending_sellers = db.scalar(select(func.count(models.SellerProfile.id)).where(models.SellerProfile.status == "pending")) or 0
    active_products = db.scalar(select(func.count(models.Product.id)).where(models.Product.is_active.is_(True))) or 0
    total_orders = db.scalar(select(func.count(models.Order.id))) or 0
    unpaid_orders = db.scalar(select(func.count(models.Order.id)).where(models.Order.payment_status == "unpaid")) or 0
    paid_sales_ugx = db.scalar(select(func.coalesce(func.sum(models.Order.total_ugx), 0)).where(models.Order.payment_status == "paid")) or 0
    return {
        "customers": total_customers,
        "sellers": total_sellers,
        "pending_sellers": pending_sellers,
        "active_products": active_products,
        "orders": total_orders,
        "unpaid_orders": unpaid_orders,
        "paid_sales_ugx": int(paid_sales_ugx),
        "currency": "UGX",
    }


@app.get("/admin/sellers/all")
def admin_list_sellers(status_filter: str | None = None, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    query = select(models.SellerProfile, models.User).join(models.User, models.User.id == models.SellerProfile.user_id)
    if status_filter in {"pending", "approved", "rejected", "suspended"}:
        query = query.where(models.SellerProfile.status == status_filter)
    elif status_filter:
        raise HTTPException(status_code=422, detail="Unsupported seller status filter")
    rows = db.execute(query.order_by(models.SellerProfile.id.desc()).limit(200)).all()
    return [
        {"id": profile.id, "user_id": account.id, "store_name": profile.store_name,
         "description": profile.description, "status": profile.status,
         "seller_name": account.full_name, "email": account.email, "phone": account.phone}
        for profile, account in rows
    ]


@app.get("/admin/products")
def admin_list_products(user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(models.Product, models.SellerProfile)
        .join(models.SellerProfile, models.SellerProfile.id == models.Product.seller_id)
        .order_by(models.Product.created_at.desc()).limit(200)
    ).all()
    return [
        {"id": product.id, "seller_id": seller.id, "store_name": seller.store_name,
         "name": product.name, "category": product.category, "price_ugx": product.price_ugx,
         "stock_quantity": product.stock_quantity, "is_active": product.is_active}
        for product, seller in rows
    ]


@app.post("/admin/products/{product_id}/deactivate")
def admin_deactivate_product(product_id: int, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()
    return {"id": product.id, "is_active": product.is_active}


@app.post("/admin/products/{product_id}/activate")
def admin_activate_product(product_id: int, user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    seller = db.get(models.SellerProfile, product.seller_id)
    if not seller or seller.status != "approved":
        raise HTTPException(status_code=409, detail="Only products from approved sellers can be activated")
    product.is_active = True
    db.commit()
    return {"id": product.id, "is_active": product.is_active}


@app.get("/admin/orders")
def admin_list_orders(user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    orders = db.scalars(
        select(models.Order).options(selectinload(models.Order.items))
        .order_by(models.Order.created_at.desc()).limit(200)
    ).all()
    return [
        {"id": order.id, "customer_id": order.customer_id, "status": order.status,
         "payment_status": order.payment_status, "payment_method": order.payment_method,
         "fulfilment_method": order.fulfilment_method, "total_ugx": order.total_ugx,
         "created_at": order.created_at,
         "items": [{"product_name": item.product_name, "quantity": item.quantity,
                    "seller_id": item.seller_id, "line_total_ugx": item.line_total_ugx}
                   for item in order.items]}
        for order in orders
    ]


@app.patch("/admin/orders/{order_id}/status")
def admin_update_order_status(order_id: int, payload: schemas.AdminOrderStatus,
                              user: models.User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    allowed_transitions = {
        "awaiting_payment": {"processing"},
        "processing": {"dispatched"},
        "dispatched": {"delivered"},
    }
    if payload.status not in allowed_transitions.get(order.status, set()):
        raise HTTPException(status_code=409, detail=f"Cannot change order status from {order.status} to {payload.status}")
    if order.payment_status != "paid":
        raise HTTPException(status_code=409, detail="An order cannot progress until payment is confirmed by a trusted payment integration")
    order.status = payload.status
    db.commit()
    return {"id": order.id, "status": order.status, "payment_status": order.payment_status}


@app.get("/admin/dashboard", include_in_schema=False)
def admin_dashboard():
    # The dashboard shell is public; every data-changing API remains admin-authenticated.
    from pathlib import Path
    return FileResponse(Path(__file__).with_name("admin_dashboard.html"))


@app.get("/seller/portal", include_in_schema=False)
def seller_portal():
    from pathlib import Path
    return FileResponse(Path(__file__).with_name("seller_portal.html"))


@app.get("/seller/products")
def seller_products(user: models.User = Depends(require_role("seller")), db: Session = Depends(get_db)):
    profile = db.scalar(select(models.SellerProfile).where(models.SellerProfile.user_id == user.id))
    if not profile:
        raise HTTPException(status_code=404, detail="Seller profile not found")
    return db.scalars(select(models.Product).where(models.Product.seller_id == profile.id).order_by(models.Product.created_at.desc())).all()


@app.get("/", include_in_schema=False)
def marketplace_home():
    from pathlib import Path
    return FileResponse(Path(__file__).with_name("marketplace.html"))
