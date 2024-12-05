import base64
import boto3
import re
from datetime import datetime
from typing import List, Dict
from .base import ToolResult
from ...core import app_logger


class FlightTools:
    def __init__(self):
        self.textract_client = boto3.client('textract')

    # remove the verify_flight_info tool during the demo phase
    # async def verify_flight_info(self, flight_number: str, date: str) -> ToolResult:
    #     """
    #     Verify flight information 
    #     """
    #     try:
    #         # Mock implementation for MVP
    #         is_valid = flight_number.startswith(("CZ", "ZH", "DL", "BA"))

    #         # Parse date string to datetime
    #         try:
    #             # Try parsing various date formats
    #             parsed_date = None
    #             date_formats = [
    #                 "%d%b",  # 25MAR
    #                 "%d-%b",  # 25-MAR
    #                 "%d/%b",  # 25/MAR
    #                 "%d %b",  # 25 MAR
    #                 "%Y-%m-%d",  # 2024-03-25
    #                 "%d/%m/%Y",  # 25/03/2024
    #                 "%m/%d/%Y",  # 03/25/2024
    #             ]
                
    #             for fmt in date_formats:
    #                 try:
    #                     if len(date) <= 5:  # Short format like "25MAR"
    #                         parsed_date = datetime.strptime(date.upper(), fmt).replace(year=datetime.now().year)
    #                     else:
    #                         parsed_date = datetime.strptime(date.upper(), fmt)
    #                     break
    #                 except ValueError:
    #                     continue

    #             if parsed_date is None:
    #                 raise ValueError(f"Could not parse date: {date}")

    #         except ValueError as e:
    #             app_logger.error(f"Error parsing date: {str(e)}")
    #             return ToolResult(
    #                 success=False,
    #                 error=f"Invalid date format: {date}"
    #             )

    #         return ToolResult(
    #             success=True,
    #             data={
    #                 "is_valid": is_valid,
    #                 "flight_info": {
    #                     "airline": flight_number[:2],
    #                     "number": flight_number[2:],
    #                     "date": parsed_date.isoformat(),
    #                     "airport": "SZX"  # Mock for MVP
    #                 } if is_valid else None
    #             }
    #         )
    #     except Exception as e:
    #         app_logger.error(f"Error verifying flight info: {str(e)}")
    #         return ToolResult(
    #             success=False,
    #             error="Failed to verify flight information"
    #         )

    async def extract_flight_info(self, image_base64: str) -> ToolResult:
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
        
        # Regular expressions for matching
        flight_pattern = r'([A-Z]{2}\d{3,4})'
        date_pattern = r'(\d{1,2}(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})'
        
        for line in text_lines:
            line = line.upper()
            # Look for flight number patterns
            flight_match = re.search(flight_pattern, line)
            if flight_match:
                fields['flight_number'] = flight_match.group(1)
            
            # Look for date patterns
            date_match = re.search(date_pattern, line)
            if date_match:
                fields['date'] = date_match.group(1)
            
            # Look for seat assignments
            if 'SEAT' in line:
                seat_match = re.search(r'(?:SEAT\s*)?(\d{1,2}[A-Z])', line)
                if seat_match:
                    fields['seat'] = seat_match.group(1)
            
            # Look for passenger name
            if 'PASSENGER' in line or 'NAME' in line:
                name_parts = line.replace('PASSENGER', '').replace('NAME', '').strip().split()
                if name_parts:
                    fields['passenger_name'] = ' '.join(name_parts)
        
        return fields


# Tool definitions
FLIGHT_TOOLS = [
    # {
    #     "name": "verify_flight_info",
    #     "description": "Verify flight information",
    #     "parameters": {
    #         "flight_number": "string",
    #         "date": "string"
    #     },
    #     "required": ["flight_number", "date"]
    # },
    {
        "name": "extract_flight_info",
        "description": "Extract text information from a flight ticket image using OCR",
        "parameters": {
            "image_base64": "string"
        },
        "required": ["image_base64"]
    }
]
