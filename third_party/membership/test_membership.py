import pytest
from .service import membership_service
from .models import MembershipProfile

@pytest.mark.asyncio
async def test_membership_profile():
    # Initialize service and create table
    assert await membership_service.initialize()
    
    # Test creating new member profile
    member_id = "TEST_USER_1"
    profile = await membership_service.create_profile(
        member_id=member_id,
        first_name="John",
        last_name="Doe",
        gender="M",
        preferred_language="en"
    )
    assert profile is not None
    assert profile.member_id == member_id
    assert profile.first_name == "John"
    assert profile.last_name == "Doe"
    assert profile.gender == "M"
    assert profile.preferred_language == "en"
    assert profile.points == 0
    
    # Test updating points
    profile = await membership_service.update_points(member_id, 30)
    assert profile is not None
    assert profile.points == 30
    
    # Test getting member profile
    profile = await membership_service.get_member_profile(member_id)
    assert profile is not None
    assert profile.points == 30
    assert profile.first_name == "John"
    
    # Test updating profile fields
    profile = await membership_service.update_profile(
        member_id,
        preferred_language="es",
        first_name="Juan"
    )
    assert profile is not None
    assert profile.preferred_language == "es"
    assert profile.first_name == "Juan"
    assert profile.last_name == "Doe"  # Unchanged
    assert profile.points == 30  # Unchanged
    
    # Test preventing negative points
    profile = await membership_service.update_points(member_id, -1000)
    assert profile is not None
    assert profile.points == 0
