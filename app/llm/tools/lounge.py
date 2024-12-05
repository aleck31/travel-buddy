from datetime import datetime
from typing import List, Optional
from .base import ToolResult
from ...core import app_logger
from ...models.lounge import Lounge, LoungeAmenity
from third_party.loungebooking.service import lounge_service


async def get_available_lounges(airport_code: str, terminal: Optional[str] = None, amenities: Optional[List[str]] = None) -> ToolResult:
    """
    Get available lounges for a given airport with optional filtering by terminal and amenities
    """
    try:
        # Initialize lounge service
        if not lounge_service._initialized:
            lounge_service.initialize()
            if not lounge_service._initialized:
                return ToolResult(
                    success=False,
                    error="Failed to initialize lounge service"
                )
        
        # Search for lounges with the given criteria
        lounges = lounge_service.search_lounges(
            airport_code=airport_code,
            terminal=terminal,
            amenities=amenities
        )
        
        # Convert to Lounge model instances
        lounge_models = []
        for lounge in lounges:
            # Map amenities directly using the exact strings from the JSON
            mapped_amenities = []
            for amenity in lounge.amenities:
                try:
                    # Use the exact string from the JSON as defined in the enum
                    mapped_amenities.append(LoungeAmenity(amenity))
                except ValueError:
                    # If amenity doesn't match enum, skip it
                    continue
            
            lounge_models.append(Lounge(
                id=lounge.id,  # Use the ID from JSON data
                name=lounge.name,
                airport_code=airport_code,
                terminal=lounge.location.terminal,
                location_description=lounge.location.details,
                amenities=mapped_amenities,
                operating_hours=lounge.openingHours,
                max_stay_hours=2,  # Most lounges specify 2 hours maximum stay
                distance_to_gate="Varies",  # Default value
                rating=4.0,  # Default value
                description=f"Located in {lounge.location.area}. {lounge.location.details}"
            ))
        
        return ToolResult(
            success=True,
            data={"lounges": [lounge.model_dump() for lounge in lounge_models]}
        )
    except Exception as e:
        app_logger.error(f"Error getting available lounges: {str(e)}")
        return ToolResult(
            success=False,
            error=f"Failed to retrieve available lounges: {str(e)}"
        )


async def book_lounge(
    user_id: str,
    lounge_id: str,
    flight_number: str,
    arrival_time: datetime
) -> ToolResult:
    """
    Book a lounge for a user
    """
    try:
        # Initialize lounge service
        if not lounge_service._initialized:
            lounge_service.initialize()
            if not lounge_service._initialized:
                return ToolResult(
                    success=False,
                    error="Failed to initialize lounge service"
                )

        # Normalize lounge_id to lowercase to handle case-insensitive matching
        normalized_lounge_id = lounge_id.lower()

        # Create booking through the lounge service
        booking = await lounge_service.create_booking(
            user_id=user_id,
            lounge_id=normalized_lounge_id,
            flight_number=flight_number,
            arrival_time=arrival_time,
            phone_number="+1234567890"  # TODO: Get from user profile
        )
        
        if booking is None:
            return ToolResult(
                success=False,
                error="Insufficient points for booking or lounge not found"
            )
        
        return ToolResult(
            success=True,
            data={"booking": booking.model_dump()}
        )
    except Exception as e:
        app_logger.error(f"Error booking lounge: {str(e)}")
        return ToolResult(
            success=False,
            error=f"Failed to book lounge: {str(e)}"
        )


# Tool definitions with enhanced descriptions for Bedrock Converse API
LOUNGE_TOOLS = [
    {
        "name": "get_available_lounges",
        "description": "Search for available airport VIP lounges based on airport code, with optional filtering by terminal and amenities",
        "parameters": {
            "airport_code": {
                "type": "string",
                "description": "Three-letter IATA airport code (e.g., SZX for Shenzhen, PVG for Shanghai Pudong)"
            },
            "terminal": {
                "type": "string",
                "description": "Optional terminal number or letter (e.g., T1, T2) to filter lounges"
            },
            "amenities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of desired amenities (e.g., ['shower', 'wifi', 'buffet'])"
            }
        },
        "required": ["airport_code"]
    },
    {
        "name": "book_lounge",
        "description": "Book a VIP lounge access for a user's upcoming flight",
        "parameters": {
            "user_id": {
                "type": "string",
                "description": "Unique identifier for the user making the booking"
            },
            "lounge_id": {
                "type": "string",
                "description": "Unique identifier for the lounge (e.g., pvg_t1_fl09 for Shanghai Pudong T1 First Class Lounge)"
            },
            "flight_number": {
                "type": "string",
                "description": "Flight number for the user's upcoming flight (e.g., CZ3456)"
            },
            "arrival_time": {
                "type": "string",
                "format": "date-time",
                "description": "Expected arrival time at the lounge in ISO 8601 format"
            }
        },
        "required": ["user_id", "lounge_id", "flight_number", "arrival_time"]
    }
]
