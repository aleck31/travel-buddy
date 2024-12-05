from typing import Optional, Dict, Any
import json
from ..bedrock import BedrockLLM
from app.core import app_logger
from app.models.chat import BookingStage


class BedrockChatIntegration:
    def __init__(self):
        self.llm = BedrockLLM()
        self._initialized = False

    async def initialize(self):
        """Initialize the integration"""
        if not self._initialized:
            self._initialized = True

    async def process_message(
        self,
        session_id: str,
        user_id: str,
        message: str,
        service_type: str = "Lounge",  # Default to Lounge as it's the only implemented service
        image: Optional[str] = None,
        session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message through the Bedrock LLM
        
        Args:
            session_id: Unique session identifier
            user_id: User's ID
            message: User's message
            service_type: Type of service being requested (Lounge, Restaurant, etc.)
            image: Base64 encoded image (optional)
            session_state: Current session state including stage, flight info, etc.
            
        Returns:
            Dict containing the response and any additional data
        """
        try:
            # Initialize if needed
            if not self._initialized:
                await self.initialize()

            # For non-Lounge services, return a message about service availability
            if service_type != "Lounge":
                return {
                    "response": (
                        f"I apologize, but the {service_type} service is not yet available. "
                        "Currently, I can only assist with Lounge bookings. "
                        "Please select the Lounge service if you'd like to book an airport lounge."
                    )
                }

            # Get prompt template
            with open('app/llm/prompts/travel_buddy_prompt.txt', 'r') as f:
                prompt_template = f.read()

            # Prepare context for LLM
            context = {
                "user_message": message,
                "service_type": service_type,
                "session_state": session_state or {},
                "user_profile": await self._get_user_profile(user_id),
                "has_image": bool(image)
            }

            # Add stage-specific context
            if session_state and "current_stage" in session_state:
                context["booking_stage"] = session_state["current_stage"]
                context["flight_info"] = session_state.get("flight_info", {})
                context["selected_lounge"] = session_state.get("lounge_selection", {})

            # Generate LLM response
            llm_response = await self.llm.generate(
                prompt=prompt_template,
                context=context,
                temperature=0.7,
                max_tokens=1024
            )
            
            return {
                "response": llm_response,
                "state": session_state
            }

        except Exception as e:
            app_logger.error(f"Error processing message: {str(e)}")
            return {
                "response": (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try again or contact your account manager for assistance."
                ),
                "error": str(e)
            }

    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information for context"""
        try:
            from third_party.membership.service import membership_service
            await membership_service.initialize()
            profile = await membership_service.get_member_profile(user_id)
            
            return {
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "gender": profile.gender,
                "preferred_language": profile.preferred_language,
                "points": profile.points
            }
        except Exception as e:
            app_logger.error(f"Error getting user profile: {str(e)}")
            return {}
