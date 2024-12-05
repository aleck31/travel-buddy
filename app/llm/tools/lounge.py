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
        # Initialize lounge service if needed
        lounge_service.initialize()
        
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
                id=f"{airport_code}_{lounge.location.terminal}_{lounge.name[:2]}",
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
            error="Failed to retrieve available lounges"
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
        # Create booking through the lounge service
        booking = await lounge_service.create_booking(
            user_id=user_id,
            lounge_id=lounge_id,
            flight_number=flight_number,
            arrival_time=arrival_time,
            phone_number="+1234567890"  # TODO: Get from user profile
        )
        
        if booking is None:
            return ToolResult(
                success=False,
                error="Insufficient points for booking"
            )
        
        return ToolResult(
            success=True,
            data={"booking": booking.model_dump()}
        )
    except Exception as e:
        app_logger.error(f"Error booking lounge: {str(e)}")
        return ToolResult(
            success=False,
            error="Failed to book lounge"
        )


# Tool definitions
LOUNGE_TOOLS = [
    {
        "name": "get_available_lounges",
        "description": "Get available lounges for a given airport",
        "parameters": {
            "airport_code": "string",
            "terminal": "string (optional)",
            "amenities": "list[string] (optional)"
        },
        "required": ["airport_code"]
    },
    {
        "name": "book_lounge",
        "description": "Book a lounge for a user",
        "parameters": {
            "user_id": "string",
            "lounge_id": "string",
            "flight_number": "string",
            "arrival_time": "datetime"
        },
        "required": ["user_id", "lounge_id", "flight_number", "arrival_time"]
    }
]
