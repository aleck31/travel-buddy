# bedrock_chat.py handles LLM integration specifics
import json
from typing import Optional, Dict, Any
from ..bedrock import BedrockLLM
from app.core import app_logger
from app.llm.tools.lounge import get_available_lounges, book_lounge, LOUNGE_TOOLS
from app.llm.tools.flight import FlightTools, FLIGHT_TOOLS
from app.llm.tools.membership import check_membership_points, MEMBERSHIP_TOOLS
from app.models.chat import BookingStage


class BedrockChatIntegration:
    def __init__(self):
        self.llm = BedrockLLM()
        self.flight_tools = FlightTools()
        # Centralize all tool definitions
        self.tools = {
            "get_available_lounges": get_available_lounges,
            "book_lounge": book_lounge,
            "extract_flight_info": self.flight_tools.extract_flight_info,
            "check_membership_points": check_membership_points
        }

    async def initialize(self):
        """Initialize the integration"""
        if not hasattr(self, '_initialized'):
            self._initialized = True

    async def _execute_tool(self, tool_use: Dict[str, Any], image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a tool based on Claude's request
        
        Args:
            tool_use: Dictionary containing toolUse information from Claude
            image_path: Optional path to uploaded image file
            
        Returns:
            Tool execution result formatted for converse API
        """
        try:
            tool_name = tool_use.get("name")
            if not tool_name or tool_name not in self.tools:
                return {
                    "status": "error",
                    "content": [{
                        "text": f"Unknown or invalid tool: {tool_name}"
                    }]
                }

            params = tool_use.get("input", {})
            tool_func = self.tools[tool_name]
            
            # Handle image path for flight info extraction
            if tool_name == "extract_flight_info" and image_path:
                params["image_path"] = image_path
            
            # Execute the tool with provided parameters
            result = await tool_func(**params)
            
            # Convert ToolResult to converse API format
            if hasattr(result, 'success') and result.success:
                return {
                    "status": "success",
                    "content": [{
                        "json": result.data
                    }]
                }
            elif hasattr(result, 'success'):
                return {
                    "status": "error",
                    "content": [{
                        "text": result.error
                    }]
                }
            else:
                return {
                    "status": "success",
                    "content": [{
                        "json": result
                    }]
                }
                
        except Exception as e:
            app_logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {
                "status": "error",
                "content": [{
                    "text": f"Tool execution failed: {str(e)}"
                }]
            }

    def _get_tools_for_stage(self, stage: str) -> list:
        """Get the appropriate tools for the current booking stage"""
        if stage == BookingStage.INITIAL_ENGAGEMENT.value:
            return []  # No tools needed for initial greeting
        elif stage == BookingStage.INFO_COLLECTION.value:
            return FLIGHT_TOOLS  # Only flight tools for info collection
        elif stage in [BookingStage.LOUNGE_RECOMMENDATION.value, BookingStage.CONFIRMATION.value]:
            return LOUNGE_TOOLS  # Lounge tools for recommendations and confirmation
        elif stage == BookingStage.BOOKING_EXECUTION.value:
            return LOUNGE_TOOLS  # Lounge tools for booking
        elif stage == BookingStage.POST_BOOKING.value:
            return MEMBERSHIP_TOOLS  # Membership tools for post-booking
        return []  # Default to no tools if stage is unknown

    async def process_message(
        self,
        session_id: str,
        user_id: str,
        message: str,
        service_type: str = "Lounge",  # Default to Lounge as it's the only implemented service
        image_path: Optional[str] = None,
        session_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user message through the Bedrock LLM
        
        Args:
            session_id: Unique session identifier
            user_id: User's ID
            message: User's message
            service_type: Type of service being requested (Lounge, Restaurant, etc.)
            image_path: Path to uploaded image file (optional)
            session_state: Current session state including stage, flight info, etc.
            
        Returns:
            Dict containing the response and any additional data
        """
        try:
            # Initialize if needed
            if not hasattr(self, '_initialized'):
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

            # Get system prompt
            with open('app/llm/prompts/travel_buddy_prompt.txt', 'r') as f:
                system_prompt = f.read()            

            # Prepare context for LLM
            context = {
                "user_message": message,
                "service_type": service_type,
                "session_state": session_state or {},
                "user_profile": await self._get_user_profile(user_id),
                "has_image": bool(image_path)
            }

            # Process message with potential tool use
            response_text = ""
            current_context = context.copy()
            tool_results = []

            current_stage = session_state.get('current_stage', 'INITIAL_ENGAGEMENT')
            available_tools = self._get_tools_for_stage(current_stage)

            # Prepare request parameters
            request_params = {
                "prompt_temp": f"Current stage: {current_stage}",
                "system_prompt": system_prompt,
                "context": current_context,
                "temperature": 0.7,
                "max_tokens": 1024
            }

            # Only add tools if available for current stage
            if available_tools:
                request_params["tools"] = available_tools

            while True:
                # Generate LLM response with tools
                llm_response = await self.llm.generate(**request_params)

                # Process the response content
                if isinstance(llm_response, dict) and "output" in llm_response:
                    message = llm_response["output"].get("message", {})
                    content_items = message.get("content", [])
                    
                    for item in content_items:
                        if "text" in item:
                            response_text += item["text"]
                        elif "toolUse" in item:
                            # Execute tool and handle result
                            tool_result = await self._execute_tool(item["toolUse"], image_path)
                            tool_results.append(tool_result)
                            
                            # Add tool result to context
                            current_context["tool_result"] = tool_result
                            
                            # If tool failed, return error
                            if tool_result.get("status") == "error":
                                return {
                                    "response": f"I apologize, but I encountered an error: {tool_result['content'][0]['text']}",
                                    "error": tool_result["content"][0]["text"]
                                }
                            
                            # Update prompt with tool result
                            continue
                    
                    # If we reach here, no more tool calls
                    break
                else:
                    # Handle plain text response
                    response_text = llm_response
                    break

            return {
                "response": response_text,
                "tool_results": tool_results,
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
