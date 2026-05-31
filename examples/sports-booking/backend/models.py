from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="customer")
    nickname = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    venues = relationship("Venue", back_populates="provider", lazy="select")
    bookings = relationship("Booking", back_populates="user", lazy="select")


class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(Text, nullable=True, default="")
    capacity = Column(Integer, nullable=False, default=1)
    price_per_hour = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), nullable=False, default="active")
    provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    provider = relationship("User", back_populates="venues", lazy="select")
    bookings = relationship("Booking", back_populates="venue", lazy="select")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String(20), nullable=False)
    time_slot = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, default="booked")
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    venue = relationship("Venue", back_populates="bookings", lazy="select")
    user = relationship("User", back_populates="bookings", lazy="select")
