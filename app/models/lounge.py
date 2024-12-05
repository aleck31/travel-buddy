from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class LoungeAmenity(str, Enum):
    # Basic Amenities
    AIR_CONDITIONING = "Air Conditioning"
    WIFI = "Wifi Access"
    TELEVISION = "Television"
    FLIGHT_MONITOR = "Flight Monitor"
    TOILETS = "Toilets"
    CHARGING_STATION = "Charging station"
    DIGITAL_CARD = "Digital Card Accepted"
    
    # Food & Beverages
    SNACKS = "Snacks"
    HOT_COLD_FOOD = "Hot/Cold Food"
    NON_ALCOHOLIC_BEVERAGES = "Non-Alcoholic Beverages (Hot/Cold)"
    ALCOHOLIC_BEVERAGES = "Alcoholic Beverages"
    FRUIT = "Fruit"
    NOODLES = "Noodles"
    VEGETARIAN = "Vegetarian"
    SELF_SERVICE_DINING = "Self-Service Dining"
    
    # Business Services
    NEWSPAPER_MAGAZINES = "Newspaper/Magazines"
    PRINTING = "Printing"
    FAX = "Fax"
    COMPUTER_ACCESS = "Computer Access"
    
    # Additional Services
    LUGGAGE_STORAGE = "Luggage Storage"
    LUGGAGE_CHECK_IN = "Luggage Check-In Assistance"
    CHECK_IN_ASSISTANCE = "Check-In Assistance"
    MASSAGE_CHAIRS = "Massage Chairs"
    SHOWER_FACILITY = "Shower Facility (Chargeable)"
    FLIGHT_ANNOUNCEMENTS = "Flight Boarding Announcements"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Lounge(BaseModel):
    id: str
    name: str
    airport_code: str
    terminal: str
    location_description: str
    amenities: List[LoungeAmenity]
    operating_hours: str
    max_stay_hours: int = 2  # Most lounges specify 2 hours maximum stay
    distance_to_gate: Optional[str] = None
    rating: Optional[float] = None
    description: str
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True


class LoungeBooking(BaseModel):
    booking_id: str
    user_id: str
    lounge_id: str
    flight_number: str
    booking_date: datetime
    arrival_time: datetime
    departure_time: Optional[datetime] = None
    status: BookingStatus = BookingStatus.PENDING
    points_used: int = 1
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[dict] = None

    class Config:
        from_attributes = True
