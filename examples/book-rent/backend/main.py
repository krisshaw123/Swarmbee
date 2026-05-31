from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database import engine, get_db, Base
from models import User, Book, Borrow, UserRole, BookStatus, BorrowStatus
from schemas import (
    SendCodeRequest, RegisterRequest, LoginRequest, AuthResponse, UserOut,
    BookCreate, BookUpdate, BookOut, BookListResponse,
    BorrowCreate, BorrowOut, BorrowListResponse,
    BookStatusUpdate, AdminStats, MessageResponse, UserListResponse,
)
from auth import (
    hash_password, verify_password, create_token, get_current_user, require_role,
)

# ── Create tables ─────────────────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BookFlow 图书借阅管理系统", version="1.0.0")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory verification codes ──────────────────────────────────────────────
verification_codes: dict[str, str] = {}


# ── Helper ────────────────────────────────────────────────────────────────────

def book_to_out(book: Book) -> BookOut:
    provider_name = book.provider.nickname or book.provider.email if book.provider else None
    return BookOut(
        id=book.id,
        title=book.title,
        author=book.author,
        description=book.description or "",
        stock=book.stock,
        status=book.status,
        provider_id=book.provider_id,
        provider_name=provider_name,
        created_at=book.created_at,
        updated_at=book.updated_at,
    )


def borrow_to_out(borrow: Borrow) -> BorrowOut:
    book_title = borrow.book.title if borrow.book else None
    return BorrowOut(
        id=borrow.id,
        book_id=borrow.book_id,
        book_title=book_title,
        user_id=borrow.user_id,
        borrow_date=borrow.borrow_date,
        return_date=borrow.return_date,
        status=borrow.status,
    )


def seed_default_admin():
    """Create default admin account if not exists."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@bookflow.com").first()
        if not admin:
            admin = User(
                email="admin@bookflow.com",
                password_hash=hash_password("admin123"),
                role=UserRole.ADMIN.value,
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
    # Validate code
    stored_code = verification_codes.get(req.email)
    if req.code != (stored_code or "123456"):
        # Also accept hardcoded 123456 directly
        if req.code != "123456":
            raise HTTPException(status_code=400, detail="验证码错误")

    # Check existing user
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已被注册")

    # Validate role
    valid_roles = {UserRole.ADMIN.value, UserRole.PROVIDER.value, UserRole.CUSTOMER.value}
    if req.role not in valid_roles:
        raise HTTPException(status_code=400, detail="无效的角色类型")
    # Normal users cannot register as admin
    if req.role == UserRole.ADMIN.value:
        raise HTTPException(status_code=400, detail="无法注册管理员账号")

    # Create user
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        role=req.role,
        nickname=req.email.split("@")[0],
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
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
#  Books API (B端 - 图书提供方)
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    req: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PROVIDER.value)),
):
    """上架书籍（B端）"""
    book = Book(
        title=req.title,
        author=req.author,
        description=req.description or "",
        stock=req.stock,
        status=BookStatus.ACTIVE.value,
        provider_id=current_user.id,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book_to_out(book)


@app.get("/api/books/my", response_model=BookListResponse)
def get_my_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PROVIDER.value)),
):
    """查看我的书籍列表（B端）"""
    books = (
        db.query(Book)
        .filter(Book.provider_id == current_user.id)
        .order_by(Book.created_at.desc())
        .all()
    )
    return BookListResponse(books=[book_to_out(b) for b in books])


@app.put("/api/books/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    req: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PROVIDER.value)),
):
    """编辑书籍信息（B端，仅自己的书籍）"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    if book.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能编辑自己的书籍")

    if req.title is not None:
        book.title = req.title
    if req.author is not None:
        book.author = req.author
    if req.description is not None:
        book.description = req.description
    if req.stock is not None:
        book.stock = req.stock
    book.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(book)
    return book_to_out(book)


@app.delete("/api/books/{book_id}", response_model=MessageResponse)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.PROVIDER.value)),
):
    """下架/删除书籍（B端，仅自己的书籍）"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    if book.provider_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能操作自己的书籍")
    db.delete(book)
    db.commit()
    return MessageResponse(message="书籍已删除")


# ═════════════════════════════════════════════════════════════════════════════
#  Books API (C端 - 客户浏览)
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/books/available", response_model=BookListResponse)
def get_available_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取可借书籍列表（C端浏览）"""
    books = (
        db.query(Book)
        .filter(Book.status == BookStatus.ACTIVE.value, Book.stock > 0)
        .order_by(Book.created_at.desc())
        .all()
    )
    return BookListResponse(books=[book_to_out(b) for b in books])


# ═════════════════════════════════════════════════════════════════════════════
#  Borrow API (C端 - 借还书)
# ═════════════════════════════════════════════════════════════════════════════

@app.post("/api/borrows", response_model=BorrowOut, status_code=status.HTTP_201_CREATED)
def borrow_book(
    req: BorrowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER.value)),
):
    """借书（C端）"""
    book = db.query(Book).filter(Book.id == req.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    if book.status != BookStatus.ACTIVE.value:
        raise HTTPException(status_code=400, detail="该书已下架")
    if book.stock <= 0:
        raise HTTPException(status_code=400, detail="库存不足")

    # Check if user already has this book borrowed
    existing = (
        db.query(Borrow)
        .filter(
            Borrow.book_id == req.book_id,
            Borrow.user_id == current_user.id,
            Borrow.status == BorrowStatus.BORROWED.value,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="您已经借阅了该书，请先归还")

    # Deduct stock
    book.stock -= 1

    # Create borrow record
    borrow = Borrow(
        book_id=req.book_id,
        user_id=current_user.id,
        status=BorrowStatus.BORROWED.value,
    )
    db.add(borrow)
    db.commit()
    db.refresh(borrow)
    return borrow_to_out(borrow)


@app.put("/api/borrows/{borrow_id}/return", response_model=BorrowOut)
def return_book(
    borrow_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER.value)),
):
    """还书（C端）"""
    borrow = db.query(Borrow).filter(Borrow.id == borrow_id).first()
    if not borrow:
        raise HTTPException(status_code=404, detail="借阅记录不存在")
    if borrow.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能归还自己的借阅")
    if borrow.status == BorrowStatus.RETURNED.value:
        raise HTTPException(status_code=400, detail="该书已归还")

    # Update borrow
    borrow.status = BorrowStatus.RETURNED.value
    borrow.return_date = datetime.now(timezone.utc)

    # Restore stock
    book = db.query(Book).filter(Book.id == borrow.book_id).first()
    if book:
        book.stock += 1

    db.commit()
    db.refresh(borrow)
    return borrow_to_out(borrow)


@app.get("/api/borrows/my", response_model=BorrowListResponse)
def get_my_borrows(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER.value)),
):
    """查看我的借书记录（C端）"""
    borrows = (
        db.query(Borrow)
        .filter(Borrow.user_id == current_user.id)
        .order_by(Borrow.borrow_date.desc())
        .all()
    )
    return BorrowListResponse(borrows=[borrow_to_out(b) for b in borrows])


# ═════════════════════════════════════════════════════════════════════════════
#  Admin API
# ═════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/stats", response_model=AdminStats)
def admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """系统统计概览"""
    total_users = db.query(User).count()
    total_books = db.query(Book).count()
    active_borrows = (
        db.query(Borrow)
        .filter(Borrow.status == BorrowStatus.BORROWED.value)
        .count()
    )
    total_borrows = db.query(Borrow).count()
    return AdminStats(
        total_users=total_users,
        total_books=total_books,
        active_borrows=active_borrows,
        total_borrows=total_borrows,
    )


@app.get("/api/admin/users", response_model=UserListResponse)
def admin_list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """获取所有用户列表"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return UserListResponse(users=[UserOut.model_validate(u) for u in users])


@app.delete("/api/admin/users/{user_id}", response_model=MessageResponse)
def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """删除用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    if user.role == UserRole.ADMIN.value:
        raise HTTPException(status_code=400, detail="不能删除管理员账号")

    # Delete associated borrows and books
    db.query(Borrow).filter(Borrow.user_id == user_id).delete()
    db.query(Book).filter(Book.provider_id == user_id).delete()
    db.delete(user)
    db.commit()
    return MessageResponse(message="用户已删除")


@app.get("/api/admin/books", response_model=BookListResponse)
def admin_list_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """获取所有书籍列表"""
    books = db.query(Book).order_by(Book.created_at.desc()).all()
    return BookListResponse(books=[book_to_out(b) for b in books])


@app.put("/api/admin/books/{book_id}/status", response_model=BookOut)
def admin_update_book_status(
    book_id: int,
    req: BookStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """修改书籍状态（上架/下架）"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    book.status = req.status
    book.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(book)
    return book_to_out(book)


@app.delete("/api/admin/books/{book_id}", response_model=MessageResponse)
def admin_delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN.value)),
):
    """删除书籍（管理员）"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="书籍不存在")
    # Delete associated borrows
    db.query(Borrow).filter(Borrow.book_id == book_id).delete()
    db.delete(book)
    db.commit()
    return MessageResponse(message="书籍已删除")


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "BookFlow API is running", "docs": "/docs"}


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
