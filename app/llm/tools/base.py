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
