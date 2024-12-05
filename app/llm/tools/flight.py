import boto3
import re
from datetime import datetime
from typing import List, Dict
from .base import Tool, ToolResult
from ...core import app_logger


class FlightTools:
    def __init__(self):
        self.textract_client = boto3.client('textract')

    async def extract_flight_info(self, image_path: str) -> ToolResult:
        """
        Extract text information from a flight ticket image using AWS Textract
        
        Args:
            image_path: Path to the uploaded image file
        """
        try:
            # Read image file
            with open(image_path, 'rb') as image_file:
                image_bytes = image_file.read()
            
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
            flight_info = self._process_extracted_text(extracted_text)
            
            # Add raw text for debugging/verification
            flight_info['raw_text'] = extracted_text
            
            # Validate extracted information
            if not flight_info['flight_number']:
                return ToolResult(
                    success=False,
                    error="Could not find a valid flight number in the image"
                )
            
            if not flight_info['date']:
                return ToolResult(
                    success=False,
                    error="Could not find a valid date in the image"
                )
            
            return ToolResult(
                success=True,
                data=flight_info
            )
            
        except FileNotFoundError:
            return ToolResult(
                success=False,
                error=f"Image file not found: {image_path}"
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
        
        Args:
            text_lines: List of text lines extracted from the image
            
        Returns:
            Dictionary containing identified flight information
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
        flight_pattern = r'([A-Z]{2}\d{3,4})'  # e.g., CZ3456
        date_pattern = r'(\d{1,2}(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)|\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})'
        airport_pattern = r'\b([A-Z]{3})\b'  # Three-letter airport codes
        
        for line in text_lines:
            line = line.upper()
            
            # Look for flight number patterns
            flight_match = re.search(flight_pattern, line)
            if flight_match and not fields['flight_number']:
                fields['flight_number'] = flight_match.group(1)
            
            # Look for date patterns
            date_match = re.search(date_pattern, line)
            if date_match and not fields['date']:
                fields['date'] = date_match.group(1)
            
            # Look for airport codes
            airport_matches = re.finditer(airport_pattern, line)
            airports = list(airport_matches)
            if len(airports) == 2:
                # If we find two airport codes in one line, assume departure->arrival
                fields['departure'] = airports[0].group(1)
                fields['arrival'] = airports[1].group(1)
            elif len(airports) == 1 and 'TO' in line:
                # If we find "TO" in the line, the airport is probably arrival
                fields['arrival'] = airports[0].group(1)
            elif len(airports) == 1 and 'FROM' in line:
                # If we find "FROM" in the line, the airport is probably departure
                fields['departure'] = airports[0].group(1)
            
            # Look for seat assignments
            if 'SEAT' in line:
                seat_match = re.search(r'(?:SEAT\s*)?(\d{1,2}[A-Z])', line)
                if seat_match and not fields['seat']:
                    fields['seat'] = seat_match.group(1)
            
            # Look for passenger name
            if ('PASSENGER' in line or 'NAME' in line) and not fields['passenger_name']:
                name_parts = line.replace('PASSENGER', '').replace('NAME', '').strip().split()
                if name_parts:
                    fields['passenger_name'] = ' '.join(name_parts)
        
        return fields


# Tool definitions using proper JSON schema format
EXTRACT_FLIGHT_INFO_TOOL = Tool(
    name="extract_flight_info",
    description="Extracts flight information from a ticket image including flight number, passenger name, departure/arrival airports, date, and seat assignment. Uses OCR technology to process the image and identify key details.",
    parameters={
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the uploaded flight ticket image file"
            }
        }
    },
    required=["image_path"]
)

FLIGHT_TOOLS = [EXTRACT_FLIGHT_INFO_TOOL]
