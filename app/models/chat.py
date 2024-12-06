from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class BookingStage(str, Enum):
    INITIAL_ENGAGEMENT = "Initial Engagement"
    INFO_COLLECTION = "Information Collection"
    LOUNGE_RECOMMENDATION = "Lounge Recommendation"
    CONFIRMATION = "Booking Confirmation"
    BOOKING_EXECUTION = "Booking Execution"
    POST_BOOKING = "Post-Booking Service"

    @classmethod
    def get_stage_number(cls, stage: "BookingStage") -> int:
        stages = list(BookingStage)
        return stages.index(stage) + 1

    @classmethod
    def get_stage_by_number(cls, number: int) -> "BookingStage":
        stages = list(BookingStage)
        if 1 <= number <= len(stages):
            return stages[number - 1]
        return BookingStage.INITIAL_ENGAGEMENT


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[dict] = None

    def model_dump(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class StageData(BaseModel):
    """Data specific to each booking stage"""
    flight_info: Optional[Dict[str, Any]] = None
    lounge_info: Optional[Dict[str, Any]] = None
    order_info: Optional[Dict[str, Any]] = None
    confirmation_status: bool = False
    stage_entered_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    stage_completed_at: Optional[str] = None

    def model_dump(self) -> dict:
        return {
            "flight_info": self.flight_info,
            "lounge_info": self.lounge_info,
            "order_info": self.order_info,
            "confirmation_status": self.confirmation_status,
            "stage_entered_at": self.stage_entered_at,
            "stage_completed_at": self.stage_completed_at
        }


class ChatSession(BaseModel):
    session_id: str
    user_id: str
    messages: List[ChatMessage] = []
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[dict] = None
    current_stage: BookingStage = Field(default=BookingStage.INITIAL_ENGAGEMENT)
    stage_data: StageData = Field(default_factory=StageData)
    
    @property
    def flight_info(self) -> Optional[Dict[str, Any]]:
        return self.stage_data.flight_info
    
    @flight_info.setter
    def flight_info(self, value: Optional[Dict[str, Any]]):
        self.stage_data.flight_info = value
        if value:
            self.stage_data.stage_completed_at = datetime.now().isoformat()
    
    @property
    def order_info(self) -> Optional[Dict[str, Any]]:
        return {
            "lounge_info": self.stage_data.lounge_info,
            "order_info": self.stage_data.order_info
        } if (self.stage_data.lounge_info or self.stage_data.order_info) else None
    
    @order_info.setter
    def order_info(self, value: Optional[Dict[str, Any]]):
        if value:
            if "lounge_info" in value:
                self.stage_data.lounge_info = value["lounge_info"]
            if "order_info" in value:
                self.stage_data.order_info = value["order_info"]
                self.stage_data.stage_completed_at = datetime.now().isoformat()

    def update_stage(self, new_stage: BookingStage) -> tuple[str, int]:
        """
        Update the current booking stage and return display info
        Returns: (stage_name, stage_number)
        """
        if new_stage != self.current_stage:
            # Mark completion of current stage
            self.stage_data.stage_completed_at = datetime.now().isoformat()
            # Initialize new stage
            self.current_stage = new_stage
            self.stage_data.stage_entered_at = datetime.now().isoformat()
            self.stage_data.stage_completed_at = None
            
            # Reset stage-specific data when returning to initial stage
            if new_stage == BookingStage.INITIAL_ENGAGEMENT:
                self.stage_data = StageData()
        
        return (new_stage.value, BookingStage.get_stage_number(new_stage))

    def is_stage_complete(self) -> bool:
        """Check if current stage is complete based on required data"""
        if self.current_stage == BookingStage.INITIAL_ENGAGEMENT:
            return True
        elif self.current_stage == BookingStage.INFO_COLLECTION:
            return bool(self.stage_data.flight_info)
        elif self.current_stage == BookingStage.LOUNGE_RECOMMENDATION:
            return bool(self.stage_data.lounge_info)
        elif self.current_stage == BookingStage.CONFIRMATION:
            return self.stage_data.confirmation_status
        elif self.current_stage == BookingStage.BOOKING_EXECUTION:
            return bool(self.stage_data.order_info)
        elif self.current_stage == BookingStage.POST_BOOKING:
            return bool(self.stage_data.stage_completed_at)
        return False

    def model_dump(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": [msg.model_dump() for msg in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "current_stage": self.current_stage,
            "stage_data": self.stage_data.model_dump()
        }

    @classmethod
    def from_dynamodb(cls, data: dict) -> "ChatSession":
        """
        Create a ChatSession instance from DynamoDB data
        """
        messages = [
            ChatMessage(**msg) for msg in data.get("messages", [])
        ]
        
        # Convert legacy flight_info to stage_data if needed
        stage_data = data.get("stage_data", {})
        if not stage_data and data.get("flight_info"):
            stage_data = {
                "flight_info": data["flight_info"],
                "lounge_info": None,
                "order_info": None,
                "confirmation_status": False,
                "stage_entered_at": data.get("created_at", datetime.now().isoformat()),
                "stage_completed_at": None
            }
        
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            messages=messages,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            metadata=data.get("metadata"),
            current_stage=BookingStage(data.get("current_stage", BookingStage.INITIAL_ENGAGEMENT)),
            stage_data=StageData(**(stage_data or {}))
        )
