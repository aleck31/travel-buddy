from datetime import datetime
import uuid
from typing import Dict, Optional

from ..models.chat import ChatSession, ChatMessage, MessageRole
from ..llm.integrations.bedrock_chat import BedrockChatIntegration
from .data_service import data_service

class SessionService:
    def __init__(self):
        self.chat_integration = BedrockChatIntegration()
        self.active_sessions: Dict[str, ChatSession] = {}

    async def get_or_create_session(self, user_id: str) -> ChatSession:
        """Get existing chat session or create a new one"""
        if user_id not in self.active_sessions:
            session_data = await data_service.load_latest_session(user_id)
            
            if session_data:
                session = ChatSession.from_dynamodb(session_data)
            else:
                session = ChatSession(
                    session_id=str(uuid.uuid4()),
                    user_id=user_id,
                    messages=[]
                )
                await self._save_new_session(session)
            
            self.active_sessions[user_id] = session
            
        return self.active_sessions[user_id]

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
            'flight_info': session.flight_info
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
            'flight_info': session.flight_info
        }
        await data_service.save_messages(item)

    async def process_message(self, session: ChatSession, user_id: str, message: str, service: str, image: Optional[str] = None):
        """Process a chat message through the chat integration"""
        # Prepare session state for context
        session_state = {
            "current_stage": session.current_stage,
            "flight_info": session.flight_info,
            "messages": [msg.model_dump() for msg in session.messages],
            "metadata": session.metadata
        }

        result = await self.chat_integration.process_message(
            session_id=session.session_id,
            user_id=user_id,
            message=message,
            service_type=service,
            image=image,
            session_state=session_state
        )

        # Update session with any state changes from the response
        if result.get("state"):
            if "current_stage" in result["state"]:
                session.current_stage = result["state"]["current_stage"]
            if "flight_info" in result["state"]:
                session.flight_info = result["state"]["flight_info"]
            if "metadata" in result["state"]:
                session.metadata = result["state"]["metadata"]

        return result

session_service = SessionService()
