from datetime import datetime
from typing import Optional, List
import logging

from ..core import app_logger
from ..models.chat import ChatMessage
from ..services.dynamodb import dynamodb_service
from third_party.membership.service import membership_service

class DataService:
    @staticmethod
    async def get_points_display(user_id: str) -> str:
        """Get user's points display"""
        try:
            await membership_service.initialize()
            profile = await membership_service.get_member_profile(user_id)
            if profile:
                return f"Available Points: {profile.points}"
            return "Available Points: User not found"
        except Exception as e:
            app_logger.error(f"Error checking points: {str(e)}")
            return "Available Points: Error checking points"

    @staticmethod
    async def get_profile_display(user_id: str) -> str:
        """Get user's profile display"""
        try:
            await membership_service.initialize()
            profile = await membership_service.get_member_profile(user_id)
            
            if profile:
                return f"""### User Profile
- Name: {profile.first_name} {profile.last_name}
- Gender: {profile.gender}
- Language: {profile.preferred_language}
"""
            return "User Profile: Not found"
        except Exception as e:
            app_logger.error(f"Error getting profile: {str(e)}")
            return "User Profile: Error loading profile"

    @staticmethod
    async def save_session(session_data: dict):
        """Save chat session to DynamoDB"""
        try:
            await dynamodb_service.put_item(session_data)
        except Exception as e:
            app_logger.error(f"Error saving session to DynamoDB: {str(e)}")

    @staticmethod
    async def save_messages(session_data: dict):
        """Save chat messages to DynamoDB"""
        try:
            await dynamodb_service.put_item(session_data)
        except Exception as e:
            app_logger.error(f"Error saving messages to DynamoDB: {str(e)}")

    @staticmethod
    async def load_latest_session(user_id: str) -> Optional[dict]:
        """Load the latest chat session for a user from DynamoDB"""
        try:
            sessions = await dynamodb_service.query_items(
                partition_key=f"USER#{user_id}",
                sort_key_prefix="SESSION#"
            )
            
            if sessions:
                return max(sessions, key=lambda x: x.get('updated_at', ''))
            return None
        except Exception as e:
            app_logger.error(f"Error loading session from DynamoDB: {str(e)}")
            return None

data_service = DataService()
