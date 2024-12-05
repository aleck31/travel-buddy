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


class ChatSession(BaseModel):
    session_id: str
    user_id: str
    messages: List[ChatMessage] = []
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Optional[dict] = None
    current_stage: BookingStage = Field(default=BookingStage.INITIAL_ENGAGEMENT)
    flight_info: Optional[Dict[str, Any]] = Field(default=None)
    booking_info: Optional[Dict[str, Any]] = Field(default=None)

    def model_dump(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "messages": [msg.model_dump() for msg in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "current_stage": self.current_stage,
            "flight_info": self.flight_info,
            "booking_info": self.booking_info
        }

    @classmethod
    def from_dynamodb(cls, data: dict) -> "ChatSession":
        """
        Create a ChatSession instance from DynamoDB data
        """
        messages = [
            ChatMessage(**msg) for msg in data.get("messages", [])
        ]
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            messages=messages,
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            metadata=data.get("metadata"),
            current_stage=BookingStage(data.get("current_stage", BookingStage.INITIAL_ENGAGEMENT)),
            flight_info=data.get("flight_info"),
            booking_info=data.get("booking_info")
        )

    def update_stage(self, new_stage: BookingStage) -> tuple[str, int]:
        """
        Update the current booking stage and return display info
        Returns: (stage_name, stage_number)
        """
        self.current_stage = new_stage
        return (new_stage.value, BookingStage.get_stage_number(new_stage))
