import asyncio
from app.llm.tools.lounge import get_available_lounges, book_lounge
from datetime import datetime, timedelta

async def test_booking():
    # First get available lounges
    print('Getting available lounges at PVG...')
    result = await get_available_lounges('PVG')
    print(f'Get lounges result: {result.success}')
    if result.success:
        lounges = result.data['lounges']
        print(f'Found {len(lounges)} lounges')
        for lounge in lounges:
            print(f'- {lounge['id']}: {lounge['name']}')
        
        # Try booking the first lounge
        if lounges:
            print('\nTrying to book first lounge...')
            arrival_time = datetime.now() + timedelta(hours=2)
            booking_result = await book_lounge(
                user_id='test_user_1',
                lounge_id=lounges[0]['id'],
                flight_number='MU123',
                arrival_time=arrival_time
            )
            print(f'Booking result: {booking_result.success}')
            if not booking_result.success:
                print(f'Booking error: {booking_result.error}')
            else:
                print(f'Booking data: {booking_result.data}')

asyncio.run(test_booking())


async def test_booking2():
    # Test with Shenzhen airport
    print('Getting available lounges at SZX...')
    result = await get_available_lounges('SZX')
    print(f'Get lounges result: {result.success}')
    if result.success:
        lounges = result.data['lounges']
        print(f'Found {len(lounges)} lounges')
        for lounge in lounges:
            print(f'- {lounge['id']}: {lounge['name']} (Points: {lounge.get('points_used', 'N/A')})')
        
        # Try booking a specific lounge
        print('\nTrying to book JOYEE lounge...')
        arrival_time = datetime.now() + timedelta(hours=2)
        booking_result = await book_lounge(
            user_id='test_user_2',
            lounge_id='szx_t3_joyee',
            flight_number='CZ3456',
            arrival_time=arrival_time
        )
        print(f'Booking result: {booking_result.success}')
        if not booking_result.success:
            print(f'Booking error: {booking_result.error}')
        else:
            print(f'Booking data: {booking_result.data}')


async def test_invalid_booking():
    print('Testing booking with invalid lounge ID...')
    arrival_time = datetime.now() + timedelta(hours=2)
    result = await book_lounge(
        user_id='test_user_3',
        lounge_id='invalid_id',
        flight_number='MU789',
        arrival_time=arrival_time
    )
    print(f'Booking result: {result.success}')
    print(f'Error message: {result.error}')
