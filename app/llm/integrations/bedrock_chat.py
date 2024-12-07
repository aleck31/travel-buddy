import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from ..bedrock import BedrockLLM
from app.core import app_logger
from app.models.chat import BookingStage
from app.llm.tools.base import Tool, ToolResult
from app.llm.tools.membership import check_membership_points
from app.llm.tools.flight import FlightTools
from app.llm.tools.lounge import get_available_lounges, store_lounge_info, book_lounge


class BedrockChatIntegration:
    def __init__(self):
        self.llm = BedrockLLM()
        # Set system prompt
        with open('app/llm/prompts/travel_buddy_prompt.txt', 'r') as f:
            self.system_prompt = f.read()
        
        # Create a mapping of tool names to their functions
        self.tool_functions = {
            "get_available_lounges": get_available_lounges,
            "store_lounge_info": store_lounge_info,
            "book_lounge": book_lounge,
            "check_flight_document": FlightTools().check_flight_document,
            "check_membership_points": check_membership_points
        }

    async def initialize(self):
        """Initialize the integration"""
        if not hasattr(self, '_initialized'):
            self._initialized = True

    def _get_tools_for_stage(self, stage_name: str) -> List[Dict[str, Any]]:
        """Get the appropriate Tool objects and their functions for the current booking stage"""
        tools = []
        stage_tools = BookingStage.get_stage_tools(BookingStage(stage_name))
        
        for tool in stage_tools:
            if tool.name in self.tool_functions:
                tools.append({
                    "tool": tool,
                    "function": self.tool_functions[tool.name]
                })
        
        return tools

    def _get_stage_requirements(self, stage_name: str) -> str:
        """Get the requirements for completing the current stage"""
        return BookingStage.get_stage_requirements(BookingStage(stage_name))

    def _update_session_state(self, session_state: Dict[str, Any], state_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update session state with tool results"""
        app_logger.info(f"Updating session state with: {json.dumps(state_updates)}")
        
        if not session_state:
            session_state = {}
        
        if not session_state.get('stage_data'):
            session_state['stage_data'] = {}

        # Update stage data directly from state updates
        for key, value in state_updates.items():
            if key in ['flight_info', 'lounge_info', 'order_info']:
                app_logger.info(f"Updating {key} in stage_data")
                session_state['stage_data'][key] = value

        app_logger.info(f"Updated session state: {json.dumps(session_state)}")
        return session_state

    async def process_message(
        self,
        session_id: str,
        user_id: str,
        message: str,
        service: str = "Lounge",  # Default to Lounge as it's the only implemented service
        image_path: Optional[str] = None,
        session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message through the Bedrock LLM
        
        Args:
            session_id: Unique session identifier
            user_id: User's ID
            message: User's message
            service: Type of service being requested (Lounge, Restaurant, etc.)
            image_path: Path to uploaded image file (optional)
            session_state: Current session state including stage, stage_data, etc.
            
        Returns:
            Dict containing the response and any additional data
        """
        try:
            # Initialize if needed
            if not hasattr(self, '_initialized'):
                await self.initialize()

            # For non-Lounge services, return a message about service availability
            if service != "Lounge":
                return {
                    "response": (
                        f"I apologize, but the {service} service is not yet available. "
                        "Currently, I can only assist with Lounge bookings. "
                        "Please select the Lounge service if you'd like to book an airport lounge."
                    )
                }

            prompt_temp = {
                'msg_sent_time': datetime.now(),
                'user_message': message  
            }

            # Get user profile for context
            # handle_start_chat()已经在第一次会话加入 user profile，结合应用场景分析是否有必要在每次对话都附加上
            user_profile = await self._get_user_profile(user_id)

            # Prepare context for LLM           
            context = {
                "service": f'{service} booking',
                "current_stage": session_state.get('current_stage', BookingStage.INITIAL_ENGAGEMENT.value),
                "has_image": bool(image_path),
                "image_path": image_path,
                "user_profile": user_profile,
                "session_state": session_state
            }

            current_stage_name = session_state.get('current_stage', BookingStage.INITIAL_ENGAGEMENT.value)
            app_logger.info(f"Processing message in stage: {current_stage_name}")

            available_tools = self._get_tools_for_stage(current_stage_name)
            app_logger.info(f"Available Tool(s): {[t['tool'].name for t in available_tools]}")

            # Prepare request parameters
            request_params = {
                "prompt_temp": prompt_temp,
                "system_prompt": self.system_prompt,
                "context": context,
                "temperature": 0.7,
                "max_tokens": 1024
            }

            # Only add tools if available for current stage
            if available_tools:
                request_params["tools"] = available_tools

            # Generate LLM response with tools
            response = await self.llm.generate(**request_params)

            # Handle response and state updates
            if isinstance(response, dict):
                app_logger.info(f"Received response with data: {json.dumps(response)}")
                
                # Get state updates from response
                state_updates = response.get('state', {})
                if state_updates:
                    app_logger.info(f"Processing state updates: {json.dumps(state_updates)}")
                    session_state = self._update_session_state(session_state, state_updates)
                
                # Extract text response
                response_text = response.get('response', '')
            else:
                response_text = response

            # Return the response and updated state
            result = {
                "response": response_text,
                "state": session_state.get('stage_data', {}) if session_state else {}
            }
            
            app_logger.info(f"Returning result: {json.dumps(result)}")
            return result

        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            app_logger.error(error_msg)
            return {
                "response": (
                    "I apologize, but I encountered an error processing your request. "
                    "Please try again or contact your account manager for assistance."
                ),
                "error": error_msg
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
