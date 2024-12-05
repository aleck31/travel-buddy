import json
import os
import boto3
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import uuid
from app.models.lounge import LoungeBooking, BookingStatus
from third_party.membership.service import membership_service

@dataclass
class LoungeLocation:
    terminal: str
    area: str
    details: str

@dataclass
class LoungeInfo:
    id: str  # Added id field
    name: str
    openingHours: str
    location: LoungeLocation
    amenities: List[str]
    conditions: Optional[List[str]] = None
    status: Optional[str] = None
    pointSpent: Optional[int] = None

@dataclass
class Airport:
    name: str
    code: str
    lounge: List[LoungeInfo]

class LoungeService:
    def __init__(self):
        self._data: Dict = {}
        self._initialized = False
        self._dynamodb = boto3.resource('dynamodb')
        self._sns = boto3.client('sns')
        self._table = self._dynamodb.Table('travel_buddy_bookings')

    def initialize(self) -> None:
        """Initialize the lounge service by loading data from JSON file"""
        try:
            if not self._initialized:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                json_path = os.path.join(current_dir, 'airport_lounges.json')
                
                with open(json_path, 'r') as f:
                    self._data = json.load(f)
                self._initialized = True
        except Exception as e:
            print(f"Failed to initialize lounge service: {str(e)}")
            self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure the service is initialized before use"""
        if not self._initialized:
            self.initialize()

    def _get_lounge_points(self, lounge_id: str) -> Optional[int]:
        """Get the points required for a lounge booking"""
        self._ensure_initialized()
        
        # Search through all cities and airports
        for city_data in self._data.values():
            for airport in city_data.get('airport', []):
                for lounge in airport['lounge']:
                    if lounge['id'] == lounge_id:  # Use id instead of name
                        return lounge.get('pointSpent', 1)  # Default to 1 if not specified
        return None

    def search_lounges(self, 
                      airport_name: Optional[str] = None,
                      airport_code: Optional[str] = None,
                      terminal: Optional[str] = None,
                      amenities: Optional[List[str]] = None) -> List[LoungeInfo]:
        """
        Search for lounges based on various criteria
        
        Args:
            airport_name: Name of the airport (case-insensitive partial match)
            airport_code: Airport IATA code (exact match)
            terminal: Terminal name/number (case-insensitive partial match)
            amenities: List of required amenities (case-insensitive partial match)
            
        Returns:
            List of matching LoungeInfo objects
        """
        self._ensure_initialized()
        
        results = []
        
        # Search through all cities and airports
        for city_data in self._data.values():
            for airport in city_data.get('airport', []):
                # Check if airport matches criteria
                if airport_code and airport['code'] != airport_code.upper():
                    continue
                    
                if airport_name and airport_name.lower() not in airport['name'].lower():
                    continue
                
                # Process each lounge in the airport
                for lounge_data in airport['lounge']:
                    # Skip if terminal doesn't match
                    if terminal and terminal.lower() not in lounge_data['location']['terminal'].lower():
                        continue
                        
                    # Skip if required amenities are not present
                    if amenities:
                        lounge_amenities = set(a.lower() for a in lounge_data.get('amenities', []))
                        if not all(any(req.lower() in am for am in lounge_amenities) 
                                 for req in amenities):
                            continue
                    
                    # Skip if lounge is temporarily unavailable
                    if lounge_data.get('status') == 'Temporarily Unavailable':
                        continue
                    
                    # Convert location dict to LoungeLocation object
                    location = LoungeLocation(**lounge_data['location'])
                    
                    # Create LoungeInfo object
                    lounge = LoungeInfo(
                        id=lounge_data['id'],  # Include id in the result
                        name=lounge_data['name'],
                        openingHours=lounge_data['openingHours'],
                        location=location,
                        amenities=lounge_data.get('amenities', []),
                        conditions=lounge_data.get('conditions'),
                        status=lounge_data.get('status'),
                        pointSpent=lounge_data.get('pointSpent', 1)
                    )
                    
                    results.append(lounge)
        
        return results

    async def create_booking(
        self,
        user_id: str,
        lounge_id: str,
        flight_number: str,
        arrival_time: datetime,
        phone_number: str
    ) -> Optional[LoungeBooking]:
        """
        Create a new lounge booking and send SMS notification
        
        Args:
            user_id: User ID making the booking
            lounge_id: ID of the lounge being booked
            flight_number: Flight number associated with the booking
            arrival_time: Expected arrival time at the lounge
            phone_number: Phone number for SMS notification
            
        Returns:
            LoungeBooking object representing the created booking or None if points insufficient
        """
        # Get points required for this lounge
        points_required = self._get_lounge_points(lounge_id)
        if points_required is None:
            print(f"Lounge not found: {lounge_id}")
            return None

        # Check and deduct points from membership
        member_points = await membership_service.get_member_points(user_id)
        if not member_points or member_points < points_required:
            print(f"Insufficient points for user {user_id}: has {member_points}, needs {points_required}")
            return None

        # Deduct points from membership
        await membership_service.update_points(user_id, -points_required)
        
        # Generate booking ID
        booking_id = f"BK_{uuid.uuid4().hex[:12]}"
        
        # Create booking object
        booking = LoungeBooking(
            booking_id=booking_id,
            user_id=user_id,
            lounge_id=lounge_id,
            flight_number=flight_number,
            booking_date=datetime.now(),
            arrival_time=arrival_time,
            status=BookingStatus.CONFIRMED,
            points_used=points_required
        )
        
        try:
            # Convert to DynamoDB item
            item = {
                'booking_id': booking.booking_id,
                'user_id': booking.user_id,
                'lounge_id': booking.lounge_id,
                'flight_number': booking.flight_number,
                'booking_date': booking.booking_date.isoformat(),
                'arrival_time': booking.arrival_time.isoformat(),
                'status': booking.status.value,
                'points_used': booking.points_used,
                'created_at': booking.created_at.isoformat(),
                'updated_at': booking.updated_at.isoformat()
            }
            
            # Save to DynamoDB
            self._table.put_item(Item=item)
            
            # Send SMS notification
            self._send_booking_confirmation_sms(phone_number, booking)
            
            return booking
        except Exception as e:
            print(f"Failed to create booking: {str(e)}")
            # Refund points if booking fails
            await membership_service.update_points(user_id, points_required)
            return None

    def _send_booking_confirmation_sms(self, phone_number: str, booking: LoungeBooking):
        """Send SMS notification for booking confirmation"""
        message = (
            f"Your lounge booking is confirmed!\n"
            f"Booking ID: {booking.booking_id}\n"
            f"Lounge: {booking.lounge_id}\n"
            f"Flight: {booking.flight_number}\n"
            f"Arrival Time: {booking.arrival_time.strftime('%Y-%m-%d %H:%M')}\n"
            f"Points Used: {booking.points_used}"
        )
        
        try:
            self._sns.publish(
                PhoneNumber=phone_number,
                Message=message
            )
        except Exception as e:
            # Log error but don't fail the booking
            print(f"Failed to send SMS notification: {str(e)}")

    async def get_booking(self, booking_id: str) -> Optional[LoungeBooking]:
        """
        Retrieve a booking by its ID
        
        Args:
            booking_id: ID of the booking to retrieve
            
        Returns:
            LoungeBooking object if found, None otherwise
        """
        response = self._table.get_item(Key={'booking_id': booking_id})
        item = response.get('Item')
        
        if not item:
            return None
            
        return LoungeBooking(
            booking_id=item['booking_id'],
            user_id=item['user_id'],
            lounge_id=item['lounge_id'],
            flight_number=item['flight_number'],
            booking_date=datetime.fromisoformat(item['booking_date']),
            arrival_time=datetime.fromisoformat(item['arrival_time']),
            status=BookingStatus(item['status']),
            points_used=item['points_used'],
            created_at=datetime.fromisoformat(item['created_at']),
            updated_at=datetime.fromisoformat(item['updated_at'])
        )

    async def get_user_bookings(self, user_id: str) -> List[LoungeBooking]:
        """
        Retrieve all bookings for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of LoungeBooking objects
        """
        response = self._table.query(
            IndexName='user_id-index',
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        
        bookings = []
        for item in response.get('Items', []):
            booking = LoungeBooking(
                booking_id=item['booking_id'],
                user_id=item['user_id'],
                lounge_id=item['lounge_id'],
                flight_number=item['flight_number'],
                booking_date=datetime.fromisoformat(item['booking_date']),
                arrival_time=datetime.fromisoformat(item['arrival_time']),
                status=BookingStatus(item['status']),
                points_used=item['points_used'],
                created_at=datetime.fromisoformat(item['created_at']),
                updated_at=datetime.fromisoformat(item['updated_at'])
            )
            bookings.append(booking)
            
        return bookings

    async def update_booking_status(self, booking_id: str, status: BookingStatus) -> Optional[LoungeBooking]:
        """
        Update the status of a booking
        
        Args:
            booking_id: ID of the booking to update
            status: New status to set
            
        Returns:
            Updated LoungeBooking object if found, None otherwise
        """
        response = self._table.update_item(
            Key={'booking_id': booking_id},
            UpdateExpression='SET #status = :status, updated_at = :updated_at',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': status.value,
                ':updated_at': datetime.now().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        item = response.get('Attributes')
        if not item:
            return None
            
        return LoungeBooking(
            booking_id=item['booking_id'],
            user_id=item['user_id'],
            lounge_id=item['lounge_id'],
            flight_number=item['flight_number'],
            booking_date=datetime.fromisoformat(item['booking_date']),
            arrival_time=datetime.fromisoformat(item['arrival_time']),
            status=BookingStatus(item['status']),
            points_used=item['points_used'],
            created_at=datetime.fromisoformat(item['created_at']),
            updated_at=datetime.fromisoformat(item['updated_at'])
        )

# Create a singleton instance
lounge_service = LoungeService()
