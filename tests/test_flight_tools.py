# run it using:
# PYTHONPATH=/home/ubuntu/repos/travel-buddy python tests/test_flight_tools.py
import asyncio
from pathlib import Path
from app.llm.tools.flight import FlightTools

async def test_check_flight_document():
    """Test the flight info extraction tool"""
    try:
        # Initialize the tools
        flight_tools = FlightTools()
        
        # Test user profile
        user_profile = {
            "first_name": "John",
            "last_name": "Smith"
        }
        
        print("\nTest 1: Valid image file")
        # Use a test image file
        test_image = "tests/test_flight_ticket.jpg"
        
        # Call the check_flight_document method
        result = await flight_tools.check_flight_document(
            image_path=test_image,
            user_profile=user_profile
        )
        
        # Print the results
        print("Extraction Result:")
        print(f"Success: {result.success}")
        if result.success:
            print("Extracted Data:")
            print(result.data.get("flight_info", {}))
        else:
            print(f"Error: {result.error}")
            if result.data:
                print("Partial Data:")
                print(result.data.get("flight_info", {}))
        
        print("\nTest 2: Non-existent file")
        # Test with non-existent file
        result = await flight_tools.check_flight_document(
            image_path="non_existent_file.jpg",
            user_profile=user_profile
        )
        print("Extraction Result:")
        print(f"Success: {result.success}")
        if result.success:
            print("Extracted Data:")
            print(result.data.get("flight_info", {}))
        else:
            print(f"Error: {result.error}")
            if result.data:
                print("Partial Data:")
                print(result.data.get("flight_info", {}))
            
    except Exception as e:
        print(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_check_flight_document())
