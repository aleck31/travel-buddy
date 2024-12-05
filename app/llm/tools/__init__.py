from .base import Tool, ToolResult
from .membership import check_membership_points, MEMBERSHIP_TOOLS
from .flight import FlightTools, FLIGHT_TOOLS
from .lounge import get_available_lounges, book_lounge, LOUNGE_TOOLS


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
        """Get available lounges"""
        return await get_available_lounges(airport_code, terminal, amenities)

    async def book_lounge(self, user_id: str, lounge_id: str, flight_number: str, arrival_time) -> ToolResult:
        """Book a lounge"""
        return await book_lounge(user_id, lounge_id, flight_number, arrival_time)

    # remove the verify_flight_info tool during the demo phase
    # async def verify_flight_info(self, flight_number: str, date: str) -> ToolResult:
    #     """Verify flight information"""
    #     return await self.flight_tools.verify_flight_info(flight_number, date)

    async def extract_flight_info(self, image_base64: str) -> ToolResult:
        """Extract information from ticket image"""
        return await self.flight_tools.extract_flight_info(image_base64)


# Create Tool instances from tool definitions
AVAILABLE_TOOLS = [Tool(**tool) for tool in (
    MEMBERSHIP_TOOLS +
    FLIGHT_TOOLS +
    LOUNGE_TOOLS
)]

# Export all tool functions and classes
__all__ = [
    'Tool',
    'ToolResult',
    'LLMTools',
    'check_membership_points',
    'get_available_lounges',
    'book_lounge',
    'flight_tools',
    'AVAILABLE_TOOLS'
]
