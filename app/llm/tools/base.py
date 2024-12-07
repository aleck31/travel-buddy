from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from ...core import app_logger


class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str]


class ToolResult(BaseModel):
    """Result of a tool execution"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def get_state_update(self) -> Dict[str, Any]:
        """
        Get the appropriate state update based on the tool's result.
        This helps standardize how tools communicate state changes.
        """
        if not self.success or not self.data:
            app_logger.info("No state update: Tool execution failed or no data")
            return {}

        # Map specific data fields to state updates
        state_updates = {}
        
        if "flight_info" in self.data:
            app_logger.info(f"Adding flight_info to state update: {self.data['flight_info']}")
            state_updates["flight_info"] = self.data["flight_info"]
        if "lounge_info" in self.data:
            app_logger.info(f"Adding lounge_info to state update: {self.data['lounge_info']}")
            state_updates["lounge_info"] = self.data["lounge_info"]
        if "order_info" in self.data:
            app_logger.info(f"Adding order_info to state update: {self.data['order_info']}")
            state_updates["order_info"] = self.data["order_info"]

        app_logger.info(f"Final state update: {state_updates}")
        return state_updates
