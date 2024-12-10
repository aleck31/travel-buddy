from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..llm.tools.membership import CHECK_MEMBERSHIP_POINTS_TOOL
from ..llm.tools.flight import CHECK_FLIGHT_DOC_TOOL
from ..llm.tools.lounge import GET_AVAILABLE_LOUNGES_TOOL, STORE_LOUNGE_INFO_TOOL, BOOK_LOUNGE_TOOL
from ..llm.tools.base import Tool
from ..core import app_logger


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class BookingStage(str, Enum):
    INITIAL_ENGAGEMENT = "Initial Engagement"
    INFO_COLLECTION = "Information Collection"
    LOUNGE_RECOMMENDATION = "Lounge Recommendation"
    CONFIRMATION = "Booking Confirmation"
    BOOKING_EXECUTION = "Booking Execution"
    POST_BOOKING = "Post-Booking Service"

    @classmethod
    def get_stage_number(cls, stage: 'BookingStage') -> int:
        stages = list(BookingStage)
        return stages.index(stage) + 1

    @classmethod
    def get_stage_by_number(cls, number: int) -> 'BookingStage':
        stages = list(BookingStage)
        if 1 <= number <= len(stages):
            return stages[number - 1]
        return cls.INITIAL_ENGAGEMENT

    @classmethod
    def get_stage_requirements(cls, stage: 'BookingStage') -> str:
        """Get the requirements for completing the specified stage"""
        requirements = {
            cls.INITIAL_ENGAGEMENT: "Respond to user's first message to move to information collection.",
            cls.INFO_COLLECTION: "Extract and store flight information to proceed.",
            cls.LOUNGE_RECOMMENDATION: "Search available lounges and store selected lounge information.",
            cls.CONFIRMATION: "Get user's confirmation to proceed with booking.",
            cls.BOOKING_EXECUTION: "Complete the booking process and store order information.",
            cls.POST_BOOKING: "Check membership points and provide post-booking service."
        }
        return requirements.get(stage, "No specific requirements.")

    @classmethod
    def get_stage_tools(cls, stage: 'BookingStage') -> List[Tool]:
        """Get the Tool instances available for the specified stage"""
        # Create a mapping of stages to their available tools
        stage_tools_mapping = {
            cls.INITIAL_ENGAGEMENT: [],  # No tools needed for initial greeting
            cls.INFO_COLLECTION: [CHECK_FLIGHT_DOC_TOOL],
            cls.LOUNGE_RECOMMENDATION: [GET_AVAILABLE_LOUNGES_TOOL, STORE_LOUNGE_INFO_TOOL],
            cls.CONFIRMATION: [STORE_LOUNGE_INFO_TOOL],
            cls.BOOKING_EXECUTION: [BOOK_LOUNGE_TOOL],
            cls.POST_BOOKING: [CHECK_MEMBERSHIP_POINTS_TOOL]
        }
        return stage_tools_mapping.get(stage, [])
    
    @classmethod
    def get_stage_tools_name(cls, stage: 'BookingStage') -> List[str]:
        """Get the tool names available for the specified stage"""
        return [tool.name for tool in cls.get_stage_tools(stage)]


class ChatMessage(BaseModel):
    role: MessageRole
    content: str

class StageData(BaseModel):
    """Data specific to each booking stage"""
    flight_info: Optional[Dict[str, Any]] = None
    lounge_info: Optional[Dict[str, Any]] = None
    order_info: Optional[Dict[str, Any]] = None
    confirmation_status: bool = False

class ChatSession(BaseModel):
    session_id: str
    user_id: str
    messages: List[ChatMessage] = []
    current_stage: BookingStage = BookingStage.INITIAL_ENGAGEMENT
    stage_data: Optional[StageData] = None
    metadata: Dict[str, Any] = {}
    is_completed: bool = False  # New field to track if booking flow is completed

    def initialize_stage_data(self):
        """Initialize stage data if not already present"""
        if not self.stage_data:
            app_logger.info("Initializing new stage data")
            self.stage_data = StageData()
    
    # @property
    # def flight_info(self) -> Optional[Dict[str, Any]]:
    #     self.initialize_stage_data()
    #     return self.stage_data.flight_info
    
    # @flight_info.setter
    # def flight_info(self, value: Optional[Dict[str, Any]]):
    #     self.initialize_stage_data()
    #     app_logger.info(f"Setting flight info: {value}")
    #     self.stage_data.flight_info = value
    #     if value:
    #         self.stage_data.stage_completed_at = datetime.now().isoformat()
    
    # @property
    # def order_info(self) -> Optional[Dict[str, Any]]:
    #     self.initialize_stage_data()
    #     return {
    #         "lounge_info": self.stage_data.lounge_info,
    #         "order_info": self.stage_data.order_info
    #     } if (self.stage_data.lounge_info or self.stage_data.order_info) else None
    
    # @order_info.setter
    # def order_info(self, value: Optional[Dict[str, Any]]):
    #     self.initialize_stage_data()
    #     if value:
    #         app_logger.info(f"Setting order info: {value}")
    #         if "lounge_info" in value:
    #             self.stage_data.lounge_info = value["lounge_info"]
    #         if "order_info" in value:
    #             self.stage_data.order_info = value["order_info"]
    #             self.stage_data.stage_completed_at = datetime.now().isoformat()

    def update_stage(self, new_stage: BookingStage) -> tuple[str, int]:
        """Update the current stage and return stage info"""
        self.current_stage = new_stage
        return new_stage.value, BookingStage.get_stage_number(new_stage)

    def mark_completed(self):
        """Mark the session as completed"""
        self.is_completed = True

    @classmethod
    def from_dynamodb(cls, item: dict) -> 'ChatSession':
        """Create a ChatSession instance from DynamoDB item"""
        messages = [
            ChatMessage(role=msg['role'], content=msg['content'])
            for msg in item.get('messages', [])
        ]
        
        stage_data = None
        if item.get('stage_data'):
            stage_data = StageData(**item['stage_data'])
            
        return cls(
            session_id=item['session_id'],
            user_id=item['user_id'],
            messages=messages,
            current_stage=BookingStage(item.get('current_stage', 'initial_engagement')),
            stage_data=stage_data,
            metadata=item.get('metadata', {}),
            is_completed=item.get('is_completed', False)
        )
