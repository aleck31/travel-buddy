from typing import Optional
import boto3
from .models import MembershipProfile
from app.core import settings, app_logger

class MembershipService:
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=settings.AWS_REGION
        )
        self.table_name = "travel_buddy_membership"
        self.table = None

    async def initialize(self) -> bool:
        """Initialize connection to DynamoDB table"""
        try:
            if not self.table:
                self.table = self.dynamodb.Table(self.table_name)
            # Verify table exists
            self.table.load()
            app_logger.info(f"Connected to DynamoDB table: {self.table_name}")
            return True
        except Exception as e:
            app_logger.error(f"Error connecting to DynamoDB table: {str(e)}")
            return False

    async def get_member_profile(self, member_id: str) -> Optional[MembershipProfile]:
        """Get membership profile for a member"""
        try:
            if not self.table:
                await self.initialize()
            
            response = self.table.get_item(
                Key={
                    'pk': f'MEMBER#{member_id}',
                    'sk': 'PROFILE'
                }
            )
            item = response.get('Item')
            return MembershipProfile.from_dynamodb_item(item) if item else None
        except Exception as e:
            app_logger.error(f"Error getting membership profile: {str(e)}")
            return None

    async def get_member_points(self, member_id: str) -> Optional[int]:
        """Get points for a member"""
        try:
            profile = await self.get_member_profile(member_id)
            return profile.points if profile else None
        except Exception as e:
            app_logger.error(f"Error getting member points: {str(e)}")
            return None

    async def create_profile(self, member_id: str, first_name: str, last_name: str, 
                           gender: str, preferred_language: str = 'en') -> Optional[MembershipProfile]:
        """Create a new member profile"""
        try:
            if not self.table:
                await self.initialize()
            
            profile = MembershipProfile.create(
                member_id=member_id,
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                preferred_language=preferred_language
            )
            
            self.table.put_item(Item=profile.to_dynamodb_item())
            return profile
        except Exception as e:
            app_logger.error(f"Error creating membership profile: {str(e)}")
            return None

    async def update_points(self, member_id: str, points_delta: int) -> Optional[MembershipProfile]:
        """Update points for a member"""
        try:
            if not self.table:
                await self.initialize()
            
            # Get current profile
            current = await self.get_member_profile(member_id)
            if not current:
                app_logger.error(f"Member profile not found for ID: {member_id}")
                return None
            
            # Update points
            current.points = max(0, current.points + points_delta)  # Prevent negative points
            
            # Save to DynamoDB
            self.table.put_item(Item=current.to_dynamodb_item())
            return current
        except Exception as e:
            app_logger.error(f"Error updating membership points: {str(e)}")
            return None

    async def update_profile(self, member_id: str, **updates) -> Optional[MembershipProfile]:
        """Update member profile fields"""
        try:
            if not self.table:
                await self.initialize()
            
            current = await self.get_member_profile(member_id)
            if not current:
                app_logger.error(f"Member profile not found for ID: {member_id}")
                return None
            
            # Update provided fields
            for field, value in updates.items():
                if hasattr(current, field):
                    setattr(current, field, value)
            
            self.table.put_item(Item=current.to_dynamodb_item())
            return current
        except Exception as e:
            app_logger.error(f"Error updating member profile: {str(e)}")
            return None


# Create a singleton instance
membership_service = MembershipService()
