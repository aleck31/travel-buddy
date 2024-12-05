# run it using:
# PYTHONPATH=/home/ubuntu/repos/travel-buddy python tests/test_flight_tools.py
import asyncio
from pathlib import Path
from app.llm.tools.flight import FlightTools

async def test_extract_flight_info():
    """Test the flight info extraction tool"""
    try:
        # Initialize the tools
        flight_tools = FlightTools()
        
        print("\nTest 1: Valid image file")
        # Use a test image file
        test_image = "tests/test_flight_ticket.jpg"
        
        # Call the extract_flight_info method
        result = await flight_tools.extract_flight_info(test_image)
        
        # Print the results
        print("Extraction Result:")
        print(f"Success: {result.success}")
        if result.success:
            print("Extracted Data:")
            print(result.data)
        else:
            print(f"Error: {result.error}")
        
        print("\nTest 2: Non-existent file")
        # Test with non-existent file
        result = await flight_tools.extract_flight_info("non_existent_file.jpg")
        print("Extraction Result:")
        print(f"Success: {result.success}")
        if result.success:
            print("Extracted Data:")
            print(result.data)
        else:
            print(f"Error: {result.error}")
            
    except Exception as e:
        print(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_extract_flight_info())
