from datetime import datetime
from typing import List, Optional, Dict, Any
from .base import Tool, ToolResult
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


async def store_lounge_info(lounge_id: str, lounge_name: str, arrival_time: datetime) -> ToolResult:
    """
    Store the selected lounge information for later confirmation.
    """
    try:
        # simplify this tool's functionality to only return selected lounge info in the specified format.
        # Create a standardized lounge info object
        lounge_info = {
            "id": lounge_id,
            'name': lounge_name,
            'arrival_time': arrival_time,
        }

        return ToolResult(
            success=True,
            data={"lounge_info": lounge_info}
        )
    except Exception as e:
        app_logger.error(f"Error setting lounge info: {str(e)}")
        return ToolResult(
            success=False,
            error=f"Failed to set lounge information: {str(e)}"
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
            data={"order_info": booking.model_dump()}
        )
    except Exception as e:
        app_logger.error(f"Error booking lounge: {str(e)}")
        return ToolResult(
            success=False,
            error=f"Failed to book lounge: {str(e)}"
        )


# Tool definitions using proper Tool class
GET_AVAILABLE_LOUNGES_TOOL = Tool(
    name="get_available_lounges",
    description="Search for available airport VIP lounges based on airport code, with optional filtering by terminal and amenities",
    parameters={
        "type": "object",
        "properties": {
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
        }
    },
    required=["airport_code"]
)

STORE_LOUNGE_INFO_TOOL = Tool(
    name="store_lounge_info",
    description="Store the selected lounge information for later confirmation",
    parameters={
        "type": "object",
        "properties": {
            "lounge_id": {
                "type": "string",
                "description": "Unique identifier for the selected lounge"
            },
            "lounge_name": {
                "type": "string",
                "description": "Name for the selected lounge"
            },            
            "arrival_time": {
                "type": "string",
                "format": "date-time",
                "description": "Expected arrival time at the lounge in ISO 8601 format"
            }            
        }
    },
    required=["lounge_id", "lounge_name", "arrival_time"]
)

BOOK_LOUNGE_TOOL = Tool(
    name="book_lounge",
    description="Book a VIP lounge access for a user's upcoming flight",
    parameters={
        "type": "object",
        "properties": {
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
        }
    },
    required=["user_id", "lounge_id", "flight_number", "arrival_time"]
)

LOUNGE_TOOLS = [GET_AVAILABLE_LOUNGES_TOOL, STORE_LOUNGE_INFO_TOOL, BOOK_LOUNGE_TOOL]
