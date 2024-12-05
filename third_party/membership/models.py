from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class MembershipProfile(BaseModel):
    member_id: str
    first_name: str
    last_name: str
    gender: str  # e.g., 'M', 'F', 'OTHER'
    preferred_language: str  # e.g., 'en', 'zh', 'es'
    points: int
    last_updated: str
    
    @classmethod
    def create(cls, member_id: str, first_name: str, last_name: str, 
              gender: str, preferred_language: str = 'en', points: int = 0):
        """Create a new membership profile"""
        now = datetime.utcnow().isoformat()
        
        return cls(
            member_id=member_id,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            preferred_language=preferred_language,
            points=points,
            last_updated=now
        )
    
    def to_dynamodb_item(self):
        """Convert to DynamoDB item format"""
        return {
            'pk': f'MEMBER#{self.member_id}',
            'sk': 'PROFILE',
            'first_name': self.first_name,
            'last_name': self.last_name,
            'gender': self.gender,
            'preferred_language': self.preferred_language,
            'points': self.points,
            'last_updated': self.last_updated,
            'type': 'membership_profile'
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict):
        """Create instance from DynamoDB item"""
        if not item:
            return None
            
        member_id = item['pk'].split('#')[1]
        return cls(
            member_id=member_id,
            first_name=item['first_name'],
            last_name=item['last_name'],
            gender=item['gender'],
            preferred_language=item['preferred_language'],
            points=item['points'],
            last_updated=item['last_updated']
        )
