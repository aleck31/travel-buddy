from datetime import datetime
import json
import uuid
from typing import Dict, Optional, Any

from ..models.chat import ChatSession, ChatMessage, MessageRole, BookingStage
from ..llm.integrations.bedrock_chat import BedrockChatIntegration
from .data_service import data_service
from ..core import app_logger

class SessionService:
    # Confirmation keywords that trigger transition from stage 4 to 5
    CONFIRMATION_KEYWORDS = ["ok", "confirm", "yes", "book", "proceed", "go ahead"]
    # Farewell keywords that trigger transition back to stage 1
    FAREWELL_KEYWORDS = ["thank", "bye", "goodbye", "done", "finished"]

    # Fields that can trigger stage transitions
    STATE_UPDATE_FIELDS = ["flight_info", "lounge_info", "order_info"]

    def __init__(self):
        self.chat_integration = BedrockChatIntegration()
        self.active_sessions: Dict[str, ChatSession] = {}

    def _validate_stage_data(self, session: ChatSession, required_fields: list[str]) -> bool:
        """Validate that all required fields exist in stage_data"""
        if not session.stage_data:
            return False
        return all(
            getattr(session.stage_data, field) is not None 
            for field in required_fields
        )

    def _determine_stage(self, session: ChatSession, message: str = "") -> BookingStage:
        """
        Determine the appropriate stage based on session state and message content
        Following the stage transition rules:
        Stage 1 -> 2: First message received
        Stage 2 -> 3: Flight info populated in stage_data
        Stage 3 -> 4: Lounge info added to stage_data
        Stage 4 -> 5: Confirmation status set to true
        Stage 5 -> 6: Order info stored in stage_data
        Stage 6 -> 1: Reset stage_data and return to initial stage
        """
        current_stage_num = BookingStage.get_stage_number(session.current_stage)
        message = message.lower()

        app_logger.info(f"Determining stage transition from stage {current_stage_num} ({session.current_stage.value})")
        app_logger.info(f"Current stage data: {session.stage_data.model_dump() if session.stage_data else 'None'}")

        # Only check transitions that are valid from the current stage
        match current_stage_num:
            case 6:  # POST_BOOKING
                # Verify all required data exists
                if not self._validate_stage_data(session, ["flight_info", "lounge_info", "order_info"]):
                    app_logger.warning("Missing required data in POST_BOOKING stage")
                    return BookingStage.INFO_COLLECTION

                # Check for booking completion
                if any(keyword in message for keyword in self.FAREWELL_KEYWORDS):
                    app_logger.debug(f"Farewell detected in POST_BOOKING stage: {message}")
                    session.mark_completed()
                    return BookingStage.INITIAL_ENGAGEMENT
                return session.current_stage

            case 1:  # INITIAL_ENGAGEMENT
                # Transition to INFO_COLLECTION only if there's a message
                if message:
                    app_logger.debug("First message received, transitioning to INFO_COLLECTION")
                    return BookingStage.INFO_COLLECTION
                return session.current_stage

            case 2:  # INFO_COLLECTION
                # Check for flight info only in INFO_COLLECTION stage
                if self._validate_stage_data(session, ["flight_info"]):
                    app_logger.debug(f"Flight info: {session.stage_data.flight_info}")
                    return BookingStage.LOUNGE_RECOMMENDATION
                return session.current_stage

            case 3:  # LOUNGE_RECOMMENDATION
                # Verify flight info still exists
                if not self._validate_stage_data(session, ["flight_info"]):
                    app_logger.warning("Missing flight info in LOUNGE_RECOMMENDATION stage")
                    return BookingStage.INFO_COLLECTION

                # Check for lounge info
                if self._validate_stage_data(session, ["lounge_info"]):
                    app_logger.debug(f"Lounge info: {session.stage_data.lounge_info}")
                    return BookingStage.CONFIRMATION
                return session.current_stage

            case 4:  # CONFIRMATION
                # Verify previous data still exists
                if not self._validate_stage_data(session, ["flight_info", "lounge_info"]):
                    app_logger.warning("Missing required data in CONFIRMATION stage")
                    return BookingStage.INFO_COLLECTION

                # Check for confirmation
                if any(keyword in message for keyword in self.CONFIRMATION_KEYWORDS):
                    app_logger.debug(f"Confirmation keyword detected: {message}")
                    if session.stage_data:
                        session.stage_data.confirmation_status = True
                        return BookingStage.BOOKING_EXECUTION
                return session.current_stage

            case 5:  # BOOKING_EXECUTION
                # Verify all required data exists
                if not self._validate_stage_data(session, ["flight_info", "lounge_info"]):
                    app_logger.warning("Missing required data in BOOKING_EXECUTION stage")
                    return BookingStage.INFO_COLLECTION

                # Check for order info
                if self._validate_stage_data(session, ["order_info"]):
                    app_logger.debug(f"Order info: {session.stage_data.order_info}")
                    return BookingStage.POST_BOOKING
                return session.current_stage

            case _:
                return session.current_stage

    async def get_or_create_session(self, user_id: str) -> ChatSession:
        """Get existing chat session or create a new one"""
        current_session = self.active_sessions.get(user_id)
        
        # Create new session if:
        # 1. No active session exists, or
        # 2. Current session is marked as completed
        if not current_session or current_session.is_completed:
            app_logger.info(f"Creating new session for user {user_id}")
            session = ChatSession(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                messages=[]
            )
            await self._save_new_session(session)
            self.active_sessions[user_id] = session
            return session
            
        app_logger.info(f"Using existing session {current_session.session_id} for user {user_id}")
        return current_session

    async def clear_session(self, user_id: str):
        """Clear the chat session for a user"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]

    async def _save_new_session(self, session: ChatSession):
        """Save a new chat session"""
        item = {
            'pk': f"USER#{session.user_id}",
            'sk': f"SESSION#{session.session_id}",
            'type': 'CHAT_SESSION',
            'user_id': session.user_id,
            'session_id': session.session_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'messages': [msg.model_dump() for msg in session.messages],
            'current_stage': session.current_stage,
            'stage_data': session.stage_data.model_dump() if session.stage_data else None,
            'is_completed': session.is_completed
        }
        await data_service.save_session(item)

    async def save_messages(self, session: ChatSession, messages: list[ChatMessage]):
        """Save chat messages to the session"""
        item = {
            'pk': f"USER#{session.user_id}",
            'sk': f"SESSION#{session.session_id}",
            'type': 'CHAT_SESSION',
            'user_id': session.user_id,
            'session_id': session.session_id,
            'updated_at': datetime.now().isoformat(),
            'messages': [msg.model_dump() for msg in session.messages],
            'current_stage': session.current_stage,
            'stage_data': session.stage_data.model_dump() if session.stage_data else None,
            'is_completed': session.is_completed
        }
        await data_service.save_messages(item)

    async def process_message(
        self,
        session: ChatSession,
        user_id: str,
        message: str,
        service: str,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a chat message through the chat integration"""
        # Determine and update stage based on current state and message
        new_stage = self._determine_stage(session, message)
        if new_stage != session.current_stage:
            session.update_stage(new_stage)

        # Prepare session state for context
        session_state = {
            "current_stage": session.current_stage.value,
            "stage_data": session.stage_data.model_dump() if session.stage_data else None,
            "messages": [msg.model_dump() for msg in session.messages],
            "metadata": session.metadata
        }

        result = await self.chat_integration.process_message(
            session_id=session.session_id,
            user_id=user_id,
            message=message,
            service=service,
            image_path=image_path,
            session_state=session_state
        )

        # Update session with any state changes from the response
        if result.get("state"):
            state = result["state"]
            app_logger.info(f"Received state update: {json.dumps(state)}")
            
            # Process each state update field that can trigger stage transitions
            for field in self.STATE_UPDATE_FIELDS:
                if field in state:
                    app_logger.info(f"Updating {field} in stage_data")
                    # Update the field in stage_data using the appropriate property setter
                    if not session.stage_data:
                        session.initialize_stage_data()
                    setattr(session.stage_data, field, state[field])
            
            # After updating stage_data, check for stage transition
            new_stage = self._determine_stage(session, message)
            if new_stage != session.current_stage:
                app_logger.info(f"Stage transition: {session.current_stage.value} -> {new_stage.value}")
                session.update_stage(new_stage)

            # Handle metadata updates (doesn't affect stage transitions)
            if "metadata" in state:
                session.metadata = state['metadata']

        return result

session_service = SessionService()
