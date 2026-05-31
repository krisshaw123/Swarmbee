from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import engine, get_db, Base
from models import User, Venue, Booking
from schemas import (
    SendCodeRequest, RegisterRequest, LoginRequest, AuthResponse, UserOut,
    VenueCreate, VenueUpdate, VenueOut, VenueResponse, VenueListResponse,
    BookingCreate, BookingOut, BookingResponse, BookingListResponse,
    VenueStatusUpdate, AdminStats, MessageResponse, UserListResponse,
)
from auth import (
    hash_password, verify_password, create_token,
    get_current_user, require_role,
)

# ── Create tables ─────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(title="VenueFlow 体育场馆预约系统", version="1.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory verification codes ──────────────────────────────────────────────
verification_codes: dict[str, str] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def venue_to_out(venue: Venue) -> VenueOut:
    provider_name = venue.provider.nickname or venue.provider.email if venue.provider else None
    return VenueOut(
        id=venue.id,
        name=venue.name,
        location=venue.location,
        type=venue.type,
        description=venue.description or "",
        capacity=venue.capacity,
        price_per_hour=venue.price_per_hour,
        status=venue.status,
        provider_id=venue.provider_id,
        provider_name=provider_name,
        created_at=venue.created_at,
        updated_at=venue.updated_at,
    )


def booking_to_out(booking: Booking) -> BookingOut:
    venue_name = booking.venue.name if booking.venue else None
    venue_type = booking.venue.type if booking.venue else None
    return BookingOut(
        id=booking.id,
        venue_id=booking.venue_id,
        venue_name=venue_name,
        venue_type=venue_type,
        user_id=booking.user_id,
        date=booking.date,
        time_slot=booking.time_slot,
        status=booking.status,
        cancelled_at=booking.cancelled_at,
        created_at=booking.created_at,
    )


def seed_default_admin():
    """Create default admin account if not exists."""
    from database import SessionLocal as SL
    db = SL()
    try:
        admin = db.query(User).filter(User.email == "admin@venueflow.com").first()
        if not admin:
            admin = User(
                email="admin@venueflow.com",
                password_hash=hash_password("admin123"),
                role="admin",
                nickname="管理员",
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


seed_default_admin()


# ═════════════════════════════════════════════════════════════════════════════
#  Auth API
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/auth/send-code", response_model=MessageResponse)
def send_code(req: SendCodeRequest):
    """发送验证码（硬编码为 123456）"""
    verification_codes[req.email] = "123456"
    return MessageResponse(message="验证码已发送（测试环境为 123456）")


@app.post("/api/auth/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """邮箱注册"""
    stored = verification_codes.get(req.email)
    if req.code != (stored or "123456"):
        if req.code != "123456":
            raise HTTPException(status_code=400, detail="验证码错误")

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    valid_roles = {"admin", "provider", "customer"}
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail="无效的角色类型")
    if req.role == "admin":
        raise HTTPException(status_code=400, detail="无法注册管理员账号")

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role,
        nickname=req.email.split("@")[0],
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.role, user.email)
    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
    )


@app.post("/api/auth/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """邮箱登录"""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    token = create_token(user.id, user.role, user.email)
    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
    )


@app.get("/api/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserOut.model_validate(current_user)


# ═════════════════════════════════════════════════════════════════════════════
#  Venues API (B端 - 场馆提供方)
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/venues", response_model=VenueResponse, status_code=status.HTTP_201_CREATED)
def create_venue(
    req: VenueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    """上架场馆（B端）"""
    venue = Venue(
        name=req.name,
        location=req.location,
        type=req.type,
        description=req.description or "",
        capacity=req.capacity,
        price_per_hour=req.price_per_hour,
        status="active",
        provider_id=current_user.id,
    )
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return VenueResponse(venue=venue_to_out(venue))


@app.get("/api/venues/my", response_model=VenueListResponse)
def get_my_venues(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    """查看我的场馆列表（B端）"""
    venues = (
        db.query(Venue)
        .filter(Venue.provider_id == current_user.id)
        .order_by(Venue.created_at.desc())
        .all()
    )
    return VenueListResponse(venues=[venue_to_out(v) for v in venues])


@app.put("/api/venues/{venue_id}", response_model=VenueResponse)
def update_venue(
    venue_id: int,
    req: VenueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    """编辑场馆信息（B端，仅自己的场馆）。也支持仅更新 status。"""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="场馆不存在")
    if venue.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己的场馆")

    if req.name is not None:
        venue.name = req.name
    if req.location is not None:
        venue.location = req.location
    if req.type is not None:
        venue.type = req.type
    if req.description is not None:
        venue.description = req.description
    if req.capacity is not None:
        venue.capacity = req.capacity
    if req.price_per_hour is not None:
        venue.price_per_hour = req.price_per_hour
    if req.status is not None:
        venue.status = req.status
    venue.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(venue)
    return VenueResponse(venue=venue_to_out(venue))


@app.delete("/api/venues/{venue_id}", response_model=MessageResponse)
def delete_venue(
    venue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("provider")),
):
    """下架/删除场馆（B端，仅自己的场馆）"""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="场馆不存在")
    if venue.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能操作自己的场馆")
    db.delete(venue)
    db.commit()
    return MessageResponse(message="场馆已删除")


# ═════════════════════════════════════════════════════════════════════════════
#  Venues API (C端 - 客户浏览)
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/venues/available", response_model=VenueListResponse)
def get_available_venues(
    type_filter: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取可预约场馆列表（C端浏览），支持按 type 筛选"""
    query = db.query(Venue).filter(Venue.status == "active")
    if type_filter:
        query = query.filter(Venue.type == type_filter)
    venues = query.order_by(Venue.created_at.desc()).all()
    return VenueListResponse(venues=[venue_to_out(v) for v in venues])


# ═════════════════════════════════════════════════════════════════════════════
#  Booking API (C端 - 预约)
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    req: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("customer")),
):
    """预约场馆（C端）"""
    venue = db.query(Venue).filter(Venue.id == req.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="场馆不存在")
    if venue.status != "active":
        raise HTTPException(status_code=400, detail="该场馆已下架")

    # Check for duplicate booking (same venue, date, time_slot)
    existing = (
        db.query(Booking)
        .filter(
            Booking.venue_id == req.venue_id,
            Booking.date == req.date,
            Booking.time_slot == req.time_slot,
            Booking.status == "booked",
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="该时段已被预约，请选择其他时段")

    booking = Booking(
        venue_id=req.venue_id,
        user_id=current_user.id,
        date=req.date,
        time_slot=req.time_slot,
        status="booked",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return BookingResponse(booking=booking_to_out(booking))


@app.put("/api/bookings/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("customer")),
):
    """取消预约（C端）"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能取消自己的预约")
    if booking.status == "cancelled":
        raise HTTPException(status_code=400, detail="该预约已取消")

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(booking)
    return BookingResponse(booking=booking_to_out(booking))


@app.get("/api/bookings/my", response_model=BookingListResponse)
def get_my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("customer")),
):
    """查看我的预约记录（C端）"""
    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return BookingListResponse(bookings=[booking_to_out(b) for b in bookings])


# ═════════════════════════════════════════════════════════════════════════════
#  Admin API
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """系统统计概览"""
    total_users = db.query(User).count()
    total_venues = db.query(Venue).count()
    active_bookings = (
        db.query(Booking).filter(Booking.status == "booked").count()
    )
    return AdminStats(
        total_users=total_users,
        total_venues=total_venues,
        active_bookings=active_bookings,
    )


@app.get("/api/admin/users", response_model=UserListResponse)
def admin_list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """获取所有用户列表"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return UserListResponse(users=[UserOut.model_validate(u) for u in users])


@app.delete("/api/admin/users/{user_id}", response_model=MessageResponse)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员账号")

    db.query(Booking).filter(Booking.user_id == user_id).delete()
    db.query(Venue).filter(Venue.provider_id == user_id).delete()
    db.delete(user)
    db.commit()
    return MessageResponse(message="用户已删除")


@app.get("/api/admin/venues", response_model=VenueListResponse)
def admin_list_venues(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """获取所有场馆列表"""
    venues = db.query(Venue).order_by(Venue.created_at.desc()).all()
    return VenueListResponse(venues=[venue_to_out(v) for v in venues])


@app.put("/api/admin/venues/{venue_id}/status", response_model=VenueResponse)
def admin_update_venue_status(
    venue_id: int,
    req: VenueStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """修改场馆状态（上架/下架）"""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="场馆不存在")
    venue.status = req.status
    venue.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(venue)
    return VenueResponse(venue=venue_to_out(venue))


@app.delete("/api/admin/venues/{venue_id}", response_model=MessageResponse)
def admin_delete_venue(
    venue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """删除场馆（管理员）"""
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="场馆不存在")
    db.query(Booking).filter(Booking.venue_id == venue_id).delete()
    db.delete(venue)
    db.commit()
    return MessageResponse(message="场馆已删除")


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "VenueFlow API is running", "docs": "/docs"}


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
