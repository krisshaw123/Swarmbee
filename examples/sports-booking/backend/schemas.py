from pydantic import BaseModel, Field
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


# ─── Venue ────────────────────────────────────────────────────────────────────

class VenueCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = ""
    capacity: int = Field(default=1, ge=1)
    price_per_hour: float = Field(default=0.0, ge=0)


class VenueUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=1)
    price_per_hour: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class VenueOut(BaseModel):
    id: int
    name: str
    location: str
    type: str
    description: Optional[str] = ""
    capacity: int
    price_per_hour: float
    status: str
    provider_id: int
    provider_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VenueResponse(BaseModel):
    venue: VenueOut


class VenueListResponse(BaseModel):
    venues: List[VenueOut]


# ─── Booking ──────────────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    venue_id: int
    date: str = Field(..., min_length=1)
    time_slot: str = Field(..., min_length=1)


class BookingOut(BaseModel):
    id: int
    venue_id: int
    venue_name: Optional[str] = None
    venue_type: Optional[str] = None
    user_id: int
    date: str
    time_slot: str
    status: str
    cancelled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BookingResponse(BaseModel):
    booking: BookingOut


class BookingListResponse(BaseModel):
    bookings: List[BookingOut]


# ─── Admin ────────────────────────────────────────────────────────────────────

class VenueStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|inactive)$")


class AdminStats(BaseModel):
    total_users: int
    total_venues: int
    active_bookings: int


class UserListResponse(BaseModel):
    users: List[UserOut]


class MessageResponse(BaseModel):
    message: str
