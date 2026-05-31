from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PROVIDER = "provider"
    CUSTOMER = "customer"


class BookStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class BorrowStatus(str, enum.Enum):
    BORROWED = "borrowed"
    RETURNED = "returned"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.CUSTOMER.value)
    nickname = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    books = relationship("Book", back_populates="provider", lazy="select")
    borrows = relationship("Borrow", back_populates="user", lazy="select")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    description = Column(Text, nullable=True, default="")
    stock = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default=BookStatus.ACTIVE.value)
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    provider = relationship("User", back_populates="books", lazy="select")
    borrows = relationship("Borrow", back_populates="book", lazy="select")


class Borrow(Base):
    __tablename__ = "borrows"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    borrow_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    return_date = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default=BorrowStatus.BORROWED.value)

    book = relationship("Book", back_populates="borrows", lazy="select")
    user = relationship("User", back_populates="borrows", lazy="select")
