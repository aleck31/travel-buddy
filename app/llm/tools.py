from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import base64
import boto3
from ..core import app_logger
from ..models.lounge import Lounge, LoungeBooking, LoungeAmenity, BookingStatus


class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str]


class ToolResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LLMTools:
    def __init__(self):
        self.textract_client = boto3.client('textract')

    @staticmethod
    async def check_membership_points(user_id: str) -> ToolResult:
        """
        Check user's available lounge access points
        """
        try:
            # Mock implementation for MVP
            points = 5 if user_id in ["demo1", "test_user"] else 0
            return ToolResult(
                success=True,
                data={"points": points}
            )
        except Exception as e:
            app_logger.error(f"Error checking membership points: {str(e)}")
            return ToolResult(
                success=False,
                error="Failed to check membership points"
            )

    @staticmethod
    async def verify_flight_info(flight_number: str, date: datetime) -> ToolResult:
        """
        Verify flight information
        """
        try:
            # Mock implementation for MVP
            is_valid = flight_number.startswith(("AA", "UA", "DL", "BA"))
            return ToolResult(
                success=True,
                data={
                    "is_valid": is_valid,
                    "flight_info": {
                        "airline": flight_number[:2],
                        "number": flight_number[2:],
                        "date": date,
                        "airport": "SZX"  # Mock for MVP
                    } if is_valid else None
                }
            )
        except Exception as e:
            app_logger.error(f"Error verifying flight info: {str(e)}")
            return ToolResult(
                success=False,
                error="Failed to verify flight information"
            )

    async def extract_ticket_info(self, image_base64: str) -> ToolResult:
        """
        Extract text information from a flight ticket image using AWS Textract
        """
        try:
            # Decode base64 image
            image_bytes = base64.b64decode(image_base64)
            
            # Call Textract
            response = self.textract_client.analyze_document(
                Document={'Bytes': image_bytes},
                FeatureTypes=['FORMS', 'TABLES']
            )
            
            # Extract relevant information
            extracted_text = []
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    extracted_text.append(block['Text'])
            
            # Process extracted text to identify flight details
            flight_info = {
                'raw_text': extracted_text,
                'identified_fields': self._process_extracted_text(extracted_text)
            }
            
            return ToolResult(
                success=True,
                data=flight_info
            )
        except Exception as e:
            app_logger.error(f"Error extracting ticket info: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to extract ticket information: {str(e)}"
            )

    def _process_extracted_text(self, text_lines: List[str]) -> Dict[str, str]:
        """
        Process extracted text lines to identify flight-related information
        """
        fields = {
            'flight_number': None,
            'passenger_name': None,
            'departure': None,
            'arrival': None,
            'date': None,
            'seat': None
        }
        
        for line in text_lines:
            line = line.upper()
            # Look for flight number patterns (e.g., AA1234, UA123)
            if any(carrier in line for carrier in ['AA', 'UA', 'DL', 'BA']) and any(c.isdigit() for c in line):
                fields['flight_number'] = line.strip()
            # Look for seat assignments
            elif 'SEAT' in line:
                fields['seat'] = line.strip()
            # Look for dates
            elif any(month in line for month in ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']):
                fields['date'] = line.strip()
            # Look for passenger name
            elif 'PASSENGER' in line or 'NAME' in line:
                fields['passenger_name'] = line.replace('PASSENGER', '').replace('NAME', '').strip()
        
        return fields

    @staticmethod
    async def get_available_lounges(airport_code: str) -> ToolResult:
        """
        Get available lounges for a given airport
        """
        try:
            # Mock implementation for MVP
            lounges = [
                Lounge(
                    id="SZX_T3_AL",
                    name="Shenzhen Airport domestic VIP lounge 3",
                    airport_code="SZX",
                    terminal="T3",
                    location_description="Domestic Departure, Airside - After passport control and security check, the lounge is located on the third floor of the Satellite hall",
                    amenities=[
                        LoungeAmenity.WIFI,
                        LoungeAmenity.FOOD,
                        LoungeAmenity.BUFFET,
                        LoungeAmenity.BAR
                    ],
                    operating_hours="07:00-22:00",
                    max_stay_hours=2,
                    distance_to_gate="5 minutes",
                    rating=4.5,
                    description="Premium lounge with full-service bar and food facilities"
                ),
                Lounge(
                    id="SZX_T4_SC",
                    name="Star Club Lounge",
                    airport_code="SZX",
                    terminal="T4",
                    location_description="Near Gate 48",
                    amenities=[
                        LoungeAmenity.WIFI,
                        LoungeAmenity.BUFFET,
                        LoungeAmenity.QUIET_ZONE,
                        LoungeAmenity.BUSINESS_CENTER
                    ],
                    operating_hours="06:00-23:00",
                    max_stay_hours=3,
                    distance_to_gate="8 minutes",
                    rating=4.2,
                    description="Business-focused lounge with quiet zones and workstations"
                )
            ]
            return ToolResult(
                success=True,
                data={"lounges": [lounge.model_dump() for lounge in lounges]}
            )
        except Exception as e:
            app_logger.error(f"Error getting available lounges: {str(e)}")
            return ToolResult(
                success=False,
                error="Failed to retrieve available lounges"
            )

    @staticmethod
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
            # Mock implementation for MVP
            booking = LoungeBooking(
                booking_id=f"BK_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                user_id=user_id,
                lounge_id=lounge_id,
                flight_number=flight_number,
                booking_date=datetime.now(),
                arrival_time=arrival_time,
                status=BookingStatus.CONFIRMED
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


# List of available tools for the LLM
AVAILABLE_TOOLS = [
    Tool(
        name="check_membership_points",
        description="Check user's available lounge access points",
        parameters={"user_id": "string"},
        required=["user_id"]
    ),
    Tool(
        name="verify_flight_info",
        description="Verify flight information",
        parameters={
            "flight_number": "string",
            "date": "datetime"
        },
        required=["flight_number", "date"]
    ),
    Tool(
        name="extract_ticket_info",
        description="Extract text information from a flight ticket image using OCR",
        parameters={
            "image_base64": "string"
        },
        required=["image_base64"]
    ),
    Tool(
        name="get_available_lounges",
        description="Get available lounges for a given airport",
        parameters={"airport_code": "string"},
        required=["airport_code"]
    ),
    Tool(
        name="book_lounge",
        description="Book a lounge for a user",
        parameters={
            "user_id": "string",
            "lounge_id": "string",
            "flight_number": "string",
            "arrival_time": "datetime"
        },
        required=["user_id", "lounge_id", "flight_number", "arrival_time"]
    )
]
