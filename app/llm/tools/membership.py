from .base import ToolResult
from ...core import app_logger
from third_party.membership.service import membership_service


async def check_membership_points(user_id: str) -> ToolResult:
    """
    Check user's available lounge access points from DynamoDB
    """
    try:
        # Ensure membership service is initialized
        await membership_service.initialize()
        
        # Get profile from DynamoDB
        profile = await membership_service.get_member_profile(user_id)
        if not profile:
            return ToolResult(
                success=False,
                error="Member profile not found"
            )
        
        return ToolResult(
            success=True,
            data={
                "points": profile.points,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "gender": profile.gender,
                "preferred_language": profile.preferred_language
            }
        )
    except Exception as e:
        app_logger.error(f"Error checking membership points: {str(e)}")
        return ToolResult(
            success=False,
            error="Failed to check membership points"
        )


# Tool definition
MEMBERSHIP_TOOLS = [
    {
        "name": "check_membership_points",
        "description": "Check user's available lounge access points",
        "parameters": {"user_id": "string"},
        "required": ["user_id"]
    }
]
