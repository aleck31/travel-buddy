from .base import Tool, ToolResult
from .membership import check_membership_points, MEMBERSHIP_TOOLS
from .flight import FlightTools, FLIGHT_TOOLS
from .lounge import get_available_lounges, book_lounge, store_lounge_info, LOUNGE_TOOLS


# Initialize FlightTools instance
flight_tools = FlightTools()


class LLMTools:
    def __init__(self):
        self.flight_tools = flight_tools
        self._initialized = False

    async def initialize(self):
        """Initialize tools if needed"""
        if not self._initialized:
            self._initialized = True

    async def check_membership_points(self, user_id: str) -> ToolResult:
        """Check user's membership points"""
        return await check_membership_points(user_id)

    async def get_available_lounges(self, airport_code: str, terminal: str = None, amenities: list = None) -> ToolResult:
        """Get available lounges at the specified airport"""
        return await get_available_lounges(airport_code, terminal, amenities)

    async def book_lounge(self, user_id: str, lounge_id: str, flight_number: str, arrival_time: str) -> ToolResult:
        """Book a lounge for the user"""
        return await book_lounge(user_id, lounge_id, flight_number, arrival_time)

    async def check_flight_document(self, image_path: str) -> ToolResult:
        """Extract information from ticket image"""
        return await self.flight_tools.check_flight_document(image_path)


# Export all tool functions and classes
__all__ = [
    'Tool',
    'ToolResult',
    'LLMTools',
    'check_membership_points',
    'get_available_lounges',
    'store_lounge_info',
    'book_lounge',
    'flight_tools',
    'MEMBERSHIP_TOOLS',
    'FLIGHT_TOOLS',
    'LOUNGE_TOOLS'
]
