"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal

# Example schemas (you can keep these for reference)
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Appointment Booking App Schemas

class Service(BaseModel):
    """
    Services offered for booking
    Collection name: "service"
    """
    name: str = Field(..., description="Service name, e.g., Product Strategy Call")
    description: Optional[str] = Field(None, description="Short description")
    duration_minutes: int = Field(..., ge=15, le=240, description="Length of the session")
    price: Optional[float] = Field(None, ge=0, description="Optional price")
    color: Optional[str] = Field("#6366F1", description="Hex color for UI tags")
    slug: Optional[str] = Field(None, description="URL-friendly identifier")

class Availability(BaseModel):
    """
    Weekly or specific-date availability windows
    Collection name: "availability"
    """
    service_id: str = Field(..., description="Target service id")
    consultant: Optional[str] = Field("You", description="Consultant name")
    weekday: Optional[int] = Field(None, ge=0, le=6, description="0=Mon ... 6=Sun. Use weekday OR date")
    date: Optional[str] = Field(None, description="YYYY-MM-DD. Use weekday OR date")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM 24h")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM 24h")
    timezone: Optional[str] = Field("UTC", description="IANA timezone name")

class Booking(BaseModel):
    """
    Bookings made by customers
    Collection name: "booking"
    """
    service_id: str
    service_name: Optional[str] = None
    customer_name: str
    email: EmailStr
    date: str = Field(..., description="YYYY-MM-DD")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    notes: Optional[str] = None
    status: Literal["pending","confirmed","cancelled"] = "confirmed"
