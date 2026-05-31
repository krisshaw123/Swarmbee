from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ─── Auth ─────────────────────────────────────────────────────────────────────

class SendCodeRequest(BaseModel):
    email: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    code: str
    role: str = Field(default="customer", pattern="^(admin|provider|customer)$")


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    nickname: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ─── Book ─────────────────────────────────────────────────────────────────────

class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    stock: int = Field(default=1, ge=0)


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    stock: Optional[int] = Field(None, ge=0)


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    description: Optional[str] = ""
    stock: int
    status: str
    provider_id: int
    provider_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    books: List[BookOut]


# ─── Borrow ───────────────────────────────────────────────────────────────────

class BorrowCreate(BaseModel):
    book_id: int


class BorrowOut(BaseModel):
    id: int
    book_id: int
    book_title: Optional[str] = None
    user_id: int
    borrow_date: Optional[datetime] = None
    return_date: Optional[datetime] = None
    status: str

    class Config:
        from_attributes = True


class BorrowListResponse(BaseModel):
    borrows: List[BorrowOut]


# ─── Admin ────────────────────────────────────────────────────────────────────

class BookStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|inactive)$")


class AdminStats(BaseModel):
    total_users: int
    total_books: int
    active_borrows: int
    total_borrows: int


class UserListResponse(BaseModel):
    users: List[UserOut]


# ─── Generic ──────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
