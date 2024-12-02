from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class LoungeAmenity(str, Enum):
    WIFI = "wifi"
    TV = "television"
    FOOD = 'food'    
    SNACKS = 'Snacks'
    BUFFET = "buffet"
    BAR = "bar"
    QUIET_ZONE = "quiet_zone"
    BUSINESS_CENTER = "business_center"
    SLEEPING_PODS = "sleeping_pods"


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
    max_stay_hours: int = 3
    distance_to_gate: Optional[str] = None
    rating: Optional[float] = None
    description: str
    metadata: Optional[dict] = None


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
