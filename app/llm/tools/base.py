from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str]


class ToolResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    stage_data_update: Optional[Dict[str, Any]] = None  # For updating specific stage data fields

    def get_state_update(self) -> Dict[str, Any]:
        """
        Get the appropriate state update based on the tool's result.
        This helps standardize how tools communicate state changes.
        """
        if not self.success or not self.data:
            return {}

        update = {}
        
        # Map tool results to appropriate state updates
        if "flight_info" in self.data:
            update["flight_info"] = self.data["flight_info"]
        elif "lounge_info" in self.data:
            update["lounge_info"] = self.data["lounge_info"]
        elif "order_info" in self.data:
            update["order_info"] = self.data["order_info"]
        
        # Include any explicit stage data updates
        if self.stage_data_update:
            for key, value in self.stage_data_update.items():
                if key not in update:
                    update[key] = value

        return update
