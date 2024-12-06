import json
from typing import Optional, Dict, Any, List
from ..bedrock import BedrockLLM
from app.core import app_logger
from app.llm.tools.lounge import LOUNGE_TOOLS
from app.llm.tools.flight import FLIGHT_TOOLS
from app.llm.tools.membership import MEMBERSHIP_TOOLS
from app.models.chat import BookingStage
from app.llm.tools.base import Tool, ToolResult


class BedrockChatIntegration:
    def __init__(self):
        self.llm = BedrockLLM()
        # Create a mapping of tool names to Tool objects
        self.tool_mapping = {}
        for tool in FLIGHT_TOOLS + LOUNGE_TOOLS + MEMBERSHIP_TOOLS:
            self.tool_mapping[tool.name] = tool

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
            tool_id = tool_use.get("toolUseId", "unknown")
            app_logger.info(f"Executing tool {tool_name} (ID: {tool_id})")

            if not tool_name or tool_name not in self.tool_mapping:
                error_msg = f"Unknown or invalid tool: {tool_name}"
                app_logger.error(error_msg)
                return {
                    "status": "error",
                    "toolUseId": tool_id,
                    "content": [{
                        "text": error_msg
                    }]
                }

            params = tool_use.get("input", {})
            
            # Log tool parameters (excluding sensitive data)
            safe_params = {k: v for k, v in params.items() if k not in ['user_id']}
            app_logger.info(f"Tool parameters: {json.dumps(safe_params)}")
            
            # Handle image path for flight info extraction
            if tool_name == "check_flight_document" and image_path:
                params["image_path"] = image_path
            
            # Get the tool function
            from app.llm.tools.lounge import get_available_lounges, book_lounge, store_lounge_info
            from app.llm.tools.flight import FlightTools
            from app.llm.tools.membership import check_membership_points
            
            tools = {
                "get_available_lounges": get_available_lounges,
                "book_lounge": book_lounge,
                "store_lounge_info": store_lounge_info,
                "check_flight_document": FlightTools().check_flight_document,
                "check_membership_points": check_membership_points
            }
            
            if tool_name not in tools:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            # Execute the tool
            result = await tools[tool_name](**params)
            
            # Convert ToolResult to converse API format
            if isinstance(result, ToolResult):
                if result.success:
                    # Use the standardized get_state_update method
                    state_update = result.get_state_update()
                    app_logger.info(f"Tool execution successful, state update: {json.dumps(state_update)}")
                    
                    return {
                        "status": "success",
                        "toolUseId": tool_id,
                        "content": [{
                            "json": result.data
                        }],
                        "state_update": state_update
                    }
                else:
                    error_msg = f"Tool execution failed: {result.error}"
                    app_logger.error(error_msg)
                    return {
                        "status": "error",
                        "toolUseId": tool_id,
                        "content": [{
                            "text": error_msg
                        }]
                    }
            else:
                # Handle non-ToolResult responses (legacy support)
                return {
                    "status": "success",
                    "toolUseId": tool_id,
                    "content": [{
                        "json": result
                    }]
                }
                
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            app_logger.error(error_msg)
            return {
                "status": "error",
                "toolUseId": tool_id if 'tool_id' in locals() else "unknown",
                "content": [{
                    "text": error_msg
                }]
            }

    def _get_tools_for_stage(self, stage_name: str) -> List[Tool]:
        """Get the appropriate Tool objects for the current booking stage"""
        stage_tool_names = {
            BookingStage.INITIAL_ENGAGEMENT.value: [],  # No tools needed for initial greeting
            BookingStage.INFO_COLLECTION.value: ["check_flight_document"],  # Only flight info extraction
            BookingStage.LOUNGE_RECOMMENDATION.value: ["get_available_lounges", "store_lounge_info"],  # Lounge search and select
            BookingStage.CONFIRMATION.value: ["get_available_lounges", "store_lounge_info"],  # Allow re-checking lounges
            BookingStage.BOOKING_EXECUTION.value: ["book_lounge"],  # Booking execution
            BookingStage.POST_BOOKING.value: ["check_membership_points"]  # Post-booking services
        }
        
        tool_names = stage_tool_names.get(stage_name, [])
        return [self.tool_mapping[name] for name in tool_names if name in self.tool_mapping]

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
            session_state: Current session state including stage, stage_data, etc.
            
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
            state_updates = {}

            current_stage_name = session_state.get('current_stage', BookingStage.INITIAL_ENGAGEMENT.value)
            available_tools = self._get_tools_for_stage(current_stage_name)

            app_logger.info(f"Processing message in stage: {current_stage_name}")
            app_logger.info(f"Available tools: {', '.join([tool.name for tool in available_tools]) if available_tools else 'None'}")

            # Prepare request parameters
            request_params = {
                "prompt_temp": (
                    f"Current stage: {current_stage_name}\n"
                    f"Stage requirements: {self._get_stage_requirements(current_stage_name)}"
                ),
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
                                error_msg = tool_result["content"][0]["text"]
                                app_logger.error(f"Tool execution failed: {error_msg}")
                                return {
                                    "response": f"I apologize, but I encountered an error: {error_msg}",
                                    "error": error_msg
                                }
                            
                            # Update state with tool result
                            if "state_update" in tool_result:
                                state_updates.update(tool_result["state_update"])
                                app_logger.info(f"Updated state with: {json.dumps(tool_result['state_update'])}")
                            
                            # Update prompt with tool result
                            continue
                    
                    # If we reach here, no more tool calls
                    break
                else:
                    # Handle plain text response
                    response_text = llm_response
                    break

            # Update session state with accumulated changes
            if state_updates:
                if session_state is None:
                    session_state = {}
                session_state.update(state_updates)
                app_logger.info("Session state updated successfully")

            return {
                "response": response_text,
                "tool_results": tool_results,
                "state": session_state
            }

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

    def _get_stage_requirements(self, stage_name: str) -> str:
        """Get the requirements for completing the current stage"""
        requirements = {
            BookingStage.INITIAL_ENGAGEMENT.value: "Respond to user's first message to move to information collection.",
            BookingStage.INFO_COLLECTION.value: "Extract and store flight information to proceed.",
            BookingStage.LOUNGE_RECOMMENDATION.value: "Search available lounges and store selected lounge information.",
            BookingStage.CONFIRMATION.value: "Get user's confirmation to proceed with booking.",
            BookingStage.BOOKING_EXECUTION.value: "Complete the booking process and store order information.",
            BookingStage.POST_BOOKING.value: "Check membership points and provide post-booking service."
        }
        return requirements.get(stage_name, "No specific requirements.")

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
