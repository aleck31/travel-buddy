from typing import Dict, Any, Optional
from datetime import datetime
import json
from app.llm.tools import LLMTools
from app.core import app_logger


## 注意：这里的代码是否跟 chat_handlers 里的功能重复，如果功能重复请以 chat_handlers 为准
class LoungeBookingConversationHandler:
    def __init__(self):
        self.tools = LLMTools()
        self.conversation_state: Dict[str, Any] = {}
        
    async def initialize(self):
        """Initialize the conversation handler"""
        await self.tools.initialize()

    def _get_conversation_state(self, session_id: str) -> Dict[str, Any]:
        """Get or create conversation state for a session"""
        if session_id not in self.conversation_state:
            self.conversation_state[session_id] = {
                'stage': 'initial',
                'user_info': {},
                'flight_info': {},
                'preferences': {},
                'lounge_selection': None
            }
        return self.conversation_state[session_id]

    async def handle_message(self, session_id: str, user_id: str, message: str, image: Optional[str] = None) -> str:
        """
        Handle incoming user message and return appropriate response
        
        Args:
            session_id: Unique session identifier
            user_id: User's ID
            message: User's message
            image: Base64 encoded image (optional)
            
        Returns:
            Response message
        """
        state = self._get_conversation_state(session_id)
        
        try:
            # Handle different conversation stages
            # 修改 stage 定义名称与 app.chat.BookingStage 里定义的保持一致
            if state['stage'] == 'INITIAL_ENGAGEMENT':
                return await self._handle_initial_greeting(session_id, user_id)
            
            # 设定的6个stage里不包含'collecting_preferences'，删去。从profile里读取语言偏好即可，无需收集其它偏好           
            elif state['stage'] == 'INFO_COLLECTION':
                if image:
                    return await self._handle_ticket_info(session_id, user_id, image)
                return await self._handle_flight_info_collection(session_id, user_id, message)
            
            # 设定的6个stage里不包含'collecting_visit_time'，作为demo应用，这一步可选          
            elif state['stage'] == 'LOUNGE_RECOMMENDATION':
                return await self._handle_lounge_recommendation(session_id, user_id, message)
            
            elif state['stage'] == 'CONFIRMATION':
                return await self._handle_confirmation(session_id, user_id, message)
                        
            elif state['stage'] == 'BOOKING_EXECUTION':
                return await self._handle_booking_process(session_id, user_id, message)
            
            elif state['stage'] == 'POST_BOOKING':
                # Reset conversation if user wants to book another lounge
                if 'another' in message.lower() or 'new' in message.lower():
                    self.conversation_state[session_id] = {}
                    return await self._handle_initial_greeting(session_id, user_id)
                return "Your booking is confirmed. Please let me know if you need any other assistance."

        except Exception as e:
            app_logger.error(f"Error handling message: {str(e)}")
            return ("I apologize, but I encountered an error processing your request. "
                   "Please contact your account manager at +1-555-0123 for assistance.")

    async def _handle_initial_greeting(self, session_id: str, user_id: str) -> str:
        """Handle initial greeting and check membership status"""
        state = self._get_conversation_state(session_id)
        
        # Check membership points
        points_result = await self.tools.check_membership_points(user_id)
        if not points_result.success:
            return ("I apologize, but I'm having trouble accessing your membership information. "
                   "Please contact your account manager at +1-555-0123 for assistance.")
        
        # Store user info in state
        state['user_info'] = points_result.data
        state['stage'] = 'INITIAL_ENGAGEMENT'
        
        points = points_result.data['points']
        name = points_result.data.get('preferred_name', 'valued member')
        
        # 这里不要hardcode greeting，请调用Bedrock claude模型进行回复，
        greeting = f"Welcome {name}! I'm here to assist you with booking a VIP lounge. "
        
        return greeting

    async def _handle_ticket_info(self, session_id: str, user_id: str, image: str) -> str:
        """Handle flight ticket image processing"""
        state = self._get_conversation_state(session_id)
        
        # Extract ticket info
        ticket_result = await self.tools.extract_flight_info(image)
        if not ticket_result.success:
            return ("I'm having trouble reading your ticket. Please ensure the image is clear "
                   "and try again, or type your flight details manually.")
        
        # Verify flight info
        flight_info = ticket_result.data['identified_fields']
        # 作为demo应用，这里去掉flight信息验证的环节

        # Store flight info
        state['flight_info'] = flight_info
        state['stage'] = 'collecting_visit_time'
        
        return ("I've got your flight details. "
                "When do you plan to visit the lounge? Please specify the time.")

    async def _handle_flight_info_collection(self, session_id: str, user_id: str, message: str) -> str:
        """Handle manual collection of flight information"""
        state = self._get_conversation_state(session_id)
        
        # Extract and verify flight info from message
        if 'flight' in message.lower():
            flight_verify_result = await self.tools.verify_flight_info(
                message.split()[-1],  # Assume flight number is last word
                datetime.now().strftime('%Y-%m-%d')  # Default to today
            )
            
            if not flight_verify_result.success:
                return ("I couldn't verify those flight details. "
                       "Please ensure your flight number is correct and try again.")
            
            state['flight_info'] = flight_verify_result.data
            state['stage'] = 'collecting_visit_time'
            
            return ("Thank you for providing your flight details. "
                   "When do you plan to visit the lounge? Please specify the time.")
        
        return ("Please provide your flight details including airline and flight number, "
                "or upload your boarding pass.")

    async def _handle_visit_time_collection(self, session_id: str, user_id: str, message: str) -> str:
        """Handle collection of planned lounge visit time"""
        state = self._get_conversation_state(session_id)
        
        try:
            # Store visit time
            state['flight_info']['planned_visit_time'] = message
            state['stage'] = 'recommending_lounges'
            
            # Get available lounges
            airport_code = state['flight_info'].get('airport_code', 'SZX')  # Default for demo
            lounges_result = await self.tools.get_available_lounges(
                airport_code,
                terminal=state['flight_info'].get('terminal'),
                amenities=[k for k, v in state['preferences'].items() if v and k != 'guests']
            )
            
            if not lounges_result.success:
                return ("I apologize, but I'm having trouble accessing the lounge information. "
                       "Please contact your account manager at +1-555-0123 for assistance.")
            
            # Store lounges in state
            state['available_lounges'] = lounges_result.data['lounges']
            
            # Format lounges as a table
            response = "Based on your preferences and flight details, here are the available lounges:\n\n"
            response += "╔════╦══════════════════╦════════════╦═══════════════════════════════════╗\n"
            response += "║ No ║      Lounge      ║   Points   ║            Amenities              ║\n"
            response += "╠════╬══════════════════╬════════════╬═══════════════════════════════════╣\n"
            
            for idx, lounge in enumerate(lounges_result.data['lounges'], 1):
                name = lounge['name'][:16]
                points = str(lounge.get('points_required', 2))
                amenities = ', '.join(lounge.get('amenities', []))[:35]
                
                response += f"║ {idx:2} ║ {name:<16} ║ {points:^10} ║ {amenities:<35} ║\n"
            
            response += "╚════╩══════════════════╩════════════╩═══════════════════════════════════╝\n\n"
            response += "Which lounge would you like to book? Please indicate by number or name."
            
            return response
            
        except Exception as e:
            app_logger.error(f"Error handling visit time: {str(e)}")
            return ("I'm having trouble processing your visit time. "
                   "Please provide the time in a clear format (e.g., '2:30 PM').")

    async def _handle_lounge_recommendation(self, session_id: str, user_id: str, message: str) -> str:
        """Handle lounge selection and move to confirmation"""
        state = self._get_conversation_state(session_id)
        
        # Find selected lounge
        selected_idx = -1
        try:
            selected_idx = int(message) - 1
        except ValueError:
            # Try to match by name
            message_lower = message.lower()
            for idx, lounge in enumerate(state['available_lounges']):
                if lounge['name'].lower() in message_lower:
                    selected_idx = idx
                    break
        
        if selected_idx >= 0 and selected_idx < len(state['available_lounges']):
            # Verify points again before confirmation
            points_result = await self.tools.check_membership_points(user_id)
            if not points_result.success:
                return ("I apologize, but I'm having trouble verifying your points. "
                       "Please contact your account manager at +1-555-0123 for assistance.")
            
            state['user_info'] = points_result.data  # Update points info
            state['lounge_selection'] = state['available_lounges'][selected_idx]
            state['stage'] = 'confirmation'
            
            # Prepare confirmation message
            lounge = state['lounge_selection']
            points_required = lounge.get('points_required', 2)
            available_points = state['user_info']['points']
            
            if available_points < points_required:
                return ("I apologize, but you don't have enough points for this lounge. "
                       "Would you like to see other available options?")
            
            response = (
                f"You've selected {lounge['name']}.\n\n"
                f"Booking Details:\n"
                f"- Location: {lounge['location_description']}\n"
                f"- Points required: {points_required}\n"
                f"- Your available points: {available_points}\n"
                f"- Visit time: {state['flight_info']['planned_visit_time']}\n"
                f"- Number of guests: {state['preferences'].get('guests', 0)}\n\n"
                "Would you like to proceed with the booking?"
            )
            return response
        
        return ("I couldn't identify which lounge you'd like to book. "
                "Please specify the lounge by its number or name from the list provided.")

    async def _handle_confirmation(self, session_id: str, user_id: str, message: str) -> str:
        """Handle booking confirmation"""
        state = self._get_conversation_state(session_id)
        
        if any(word in message.lower() for word in ['yes', 'proceed', 'confirm', 'book']):
            state['stage'] = 'booking'
            return await self._handle_booking_process(session_id, user_id, "proceed")
        
        if any(word in message.lower() for word in ['no', 'cancel', 'different']):
            state['stage'] = 'recommending_lounges'
            return "Let me help you select a different lounge. Here are the available options again..."
        
        return "Would you like to proceed with the booking? Please confirm with 'yes' or 'no'."

    async def _handle_booking_process(self, session_id: str, user_id: str, message: str) -> str:
        """Handle the final booking process"""
        state = self._get_conversation_state(session_id)
        
        if 'yes' in message.lower() or 'proceed' in message.lower():
            # Final points verification
            points_result = await self.tools.check_membership_points(user_id)
            if not points_result.success:
                return ("I apologize, but I'm having trouble verifying your points. "
                       "Please contact your account manager at +1-555-0123 for assistance.")
            
            points_required = state['lounge_selection'].get('points_required', 2)
            if points_result.data['points'] < points_required:
                return ("I apologize, but you no longer have sufficient points for this booking. "
                       "Would you like to see other available options?")
            
            # Attempt to book the lounge
            booking_result = await self.tools.book_lounge(
                user_id=user_id,
                lounge_id=state['lounge_selection']['id'],
                flight_number=state['flight_info'].get('flight_number', ''),
                arrival_time=state['flight_info'].get('planned_visit_time', '')
            )
            
            if not booking_result.success:
                return ("I apologize, but I couldn't complete your booking. "
                       "Please contact your account manager at +1-555-0123 for assistance.")
            
            # Update state
            state['stage'] = 'completed'
            state['booking'] = booking_result.data['booking']
            
            # Construct success message
            lounge_name = state['lounge_selection']['name']
            points_used = state['lounge_selection'].get('points_required', 2)
            remaining_points = points_result.data['points'] - points_used
            
            response = (
                f"Excellent! I've successfully booked the {lounge_name} for you.\n\n"
                f"Booking Details:\n"
                f"- Booking ID: {booking_result.data['booking']['booking_id']}\n"
                f"- Lounge: {lounge_name}\n"
                f"- Location: {state['lounge_selection']['location_description']}\n"
                f"- Visit time: {state['flight_info']['planned_visit_time']}\n"
                f"- Points used: {points_used}\n"
                f"- Remaining points: {remaining_points}\n\n"
                f"A confirmation SMS has been sent to your registered phone number.\n\n"
                "Would you like to book another lounge or is there anything else you need assistance with?"
            )
            
            return response
            
        return "Would you like me to proceed with the booking? Please confirm with 'yes' or 'no'."
