import base64
from pathlib import Path
from typing import List, Tuple, AsyncGenerator, Generator
import logging
import re
from datetime import datetime

from ...core import app_logger
from ...models.chat import ChatMessage, MessageRole, BookingStage
from ..session_service import session_service
from ..data_service import data_service
from third_party.membership.service import membership_service
from app.llm.bedrock import BedrockLLM
from app.llm.tools import LLMTools

class ChatHandlers:
    def __init__(self):
        self.llm = BedrockLLM()
        self.tools = LLMTools()

    @staticmethod
    async def handle_start_chat(
        user_id: str,
        service: str
    ) -> Tuple[str, str, List[dict], str, str, str, str, int]:
        """Handle the start chat button click"""
        try:
            if service == "Choose...":
                return "", "", [], "", "", "Please select a service to continue.", "", 0

            session = await session_service.get_or_create_session(user_id)
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            
            # Get user profile for context
            await membership_service.initialize()
            profile = await membership_service.get_member_profile(user_id)
            # 由于是demo 不需要添加过多的异常处理
            
            # Create context for LLM
            context = {
                "user_profile": {
                    "first_name": profile.first_name,
                    "last_name": profile.last_name,
                    "service": service,
                    "gender": profile.gender,
                    "preferred_language": profile.preferred_language,
                    "points": profile.points
                },
                "session_state": {
                    "current_stage": BookingStage.INITIAL_ENGAGEMENT.value,
                    "is_new_session": True
                }
            }
            
            # Generate greeting using Bedrock Claude
            with open("app/llm/prompts/travel_buddy_prompt.txt", "r") as f:
                prompt = f.read()
            
            # Create instance of BedrockLLM for static method
            llm = BedrockLLM()
            # Use generate instead of stream_generate for greeting
            greeting = await llm.generate(
                prompt=prompt,
                context=context,
                temperature=0.7,
                max_tokens=200  # Shorter response for greeting
            )
            
            history = [{"role": "assistant", "content": greeting}]

            assistant_message = ChatMessage(role=MessageRole.ASSISTANT, content=greeting)
            session.messages.append(assistant_message)
            await session_service.save_messages(session, [assistant_message])

            stage_name, stage_number = session.update_stage(BookingStage.INITIAL_ENGAGEMENT)

            return user_id, service, history, points_display, profile_display, "", stage_name, stage_number

        except Exception as e:
            app_logger.error(f"Error starting chat: {str(e)}")
            return "", "", [], "", "", "An error occurred. Please try again.", "", 0

    @staticmethod
    async def handle_message(
        message: str,
        history: List[dict],
        user_id: str,
        service: str
    ) -> Tuple[str, List[dict], str, str, str, int]:
        """Handle incoming chat messages"""
        if not message.strip():
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            session = await session_service.get_or_create_session(user_id)
            stage_name, stage_number = session.current_stage.value, BookingStage.get_stage_number(session.current_stage)
            return "", history, points_display, profile_display, stage_name, stage_number

        try:
            session = await session_service.get_or_create_session(user_id)
            result = await session_service.process_message(
                session=session,
                user_id=user_id,
                message=message,
                service=service
            )

            # Extract flight info if in info collection stage
            if session.current_stage == BookingStage.INFO_COLLECTION:
                flight_info = ChatHandlers._extract_flight_info(message)
                if flight_info:
                    session.flight_info = flight_info

            # Update stage based on conversation progress
            new_stage = ChatHandlers._determine_stage(message, result["response"], session)
            if new_stage != session.current_stage:
                stage_name, stage_number = session.update_stage(new_stage)
            else:
                stage_name, stage_number = session.current_stage.value, BookingStage.get_stage_number(session.current_stage)

            history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": result["response"]}
            ])
            
            user_message = ChatMessage(role=MessageRole.USER, content=message)
            assistant_message = ChatMessage(role=MessageRole.ASSISTANT, content=result["response"])
            session.messages.extend([user_message, assistant_message])
            await session_service.save_messages(session, [user_message, assistant_message])
            
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            
            return "", history, points_display, profile_display, stage_name, stage_number

        except Exception as e:
            app_logger.error(f"Error handling message: {str(e)}")
            error_msg = "I apologize, but I encountered an error processing your request. Please try again."
            history.append({"role": "assistant", "content": error_msg})
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            session = await session_service.get_or_create_session(user_id)
            stage_name, stage_number = session.current_stage.value, BookingStage.get_stage_number(session.current_stage)
            return "", history, points_display, profile_display, stage_name, stage_number

    @staticmethod
    async def handle_upload(
        file: Path,
        history: List[dict],
        user_id: str,
        service: str
    ) -> Tuple[List[dict], str, str, str, int]:
        """Handle uploaded flight documents"""
        try:
            with open(file.name, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            session = await session_service.get_or_create_session(user_id)
            
            # Process the upload through session service
            result = await session_service.process_message(
                session=session,
                user_id=user_id,
                message="[Uploaded flight ticket image]",
                service=service,
                image=image_base64
            )

            history.extend([
                {"role": "user", "content": "[Uploaded flight ticket image]"},
                {"role": "assistant", "content": result["response"]}
            ])

            user_message = ChatMessage(
                role=MessageRole.USER,
                content="[Uploaded flight ticket image]"
            )
            assistant_message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=result["response"]
            )
            session.messages.extend([user_message, assistant_message])
            await session_service.save_messages(session, [user_message, assistant_message])

            # Move to recommendation stage if we have flight info
            if session.flight_info:
                stage_name, stage_number = session.update_stage(BookingStage.LOUNGE_RECOMMENDATION)
            else:
                stage_name, stage_number = session.current_stage.value, BookingStage.get_stage_number(session.current_stage)

            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            return history, points_display, profile_display, stage_name, stage_number

        except Exception as e:
            app_logger.error(f"Error handling file upload: {str(e)}")
            error_msg = "I apologize, but I couldn't process your uploaded file. Please ensure it's a valid image file and try again."
            history.extend([
                {"role": "user", "content": f"[Upload failed: {file.name}]"},
                {"role": "assistant", "content": error_msg}
            ])
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            session = await session_service.get_or_create_session(user_id)
            stage_name, stage_number = session.current_stage.value, BookingStage.get_stage_number(session.current_stage)
            return history, points_display, profile_display, stage_name, stage_number

    @staticmethod
    async def handle_clear_chat(user_id: str) -> Tuple[List[dict], str, str, str, int]:
        """Clear the chat history and create a new session"""
        await session_service.clear_session(user_id)
        session = await session_service.get_or_create_session(user_id)
        points_display = await data_service.get_points_display(user_id)
        profile_display = await data_service.get_profile_display(user_id)
        stage_name, stage_number = session.current_stage.value, BookingStage.get_stage_number(session.current_stage)
        return [], points_display, profile_display, stage_name, stage_number

    @staticmethod
    async def handle_refresh_info(user_id: str) -> Tuple[str, str]:
        """Refresh user's points and profile display"""
        points_display = await data_service.get_points_display(user_id)
        profile_display = await data_service.get_profile_display(user_id)
        return points_display, profile_display

    @staticmethod
    def _extract_flight_info(message: str) -> dict:
        """Extract flight information from user message"""
        flight_info = {}
        
        # Extract flight number (e.g., CZ123, BA456)
        flight_match = re.search(r'([A-Z]{2}\d{3,4})', message.upper())
        if flight_match:
            flight_info['flight_number'] = flight_match.group(1)
        
        # Extract arrival time
        time_patterns = [
            r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))',  # 12-hour format
            r'(\d{2}:\d{2})',  # 24-hour format
            r'at\s+(\d{1,2}(?::\d{2})?)'  # Time with 'at' prefix
        ]
        
        for pattern in time_patterns:
            time_match = re.search(pattern, message.lower())
            if time_match:
                flight_info['arrival_time'] = time_match.group(1)
                break
        
        return flight_info if flight_info else None

    @staticmethod
    def _determine_stage(user_message: str, assistant_response: str, session) -> BookingStage:
        """Determine the current booking stage based on conversation context"""
        current_stage = session.current_stage
        
        # Initial engagement to info collection
        if current_stage == BookingStage.INITIAL_ENGAGEMENT and any(
            keyword in user_message.lower() for keyword in ["book", "lounge", "yes", "help"]
        ):
            return BookingStage.INFO_COLLECTION
            
        # Info collection to lounge recommendation
        if current_stage == BookingStage.INFO_COLLECTION:
            if session.flight_info and session.flight_info.get('flight_number'):
                return BookingStage.LOUNGE_RECOMMENDATION
            
        # Lounge recommendation to confirmation
        if current_stage == BookingStage.LOUNGE_RECOMMENDATION and any(
            keyword in user_message.lower() for keyword in ["select", "choose", "book", "yes", "confirm"]
        ):
            return BookingStage.CONFIRMATION
            
        # Confirmation to booking execution
        if current_stage == BookingStage.CONFIRMATION and any(
            keyword in user_message.lower() for keyword in ["proceed", "yes", "confirm", "book"]
        ):
            return BookingStage.BOOKING_EXECUTION
            
        # Booking execution to post-booking
        if current_stage == BookingStage.BOOKING_EXECUTION and any(
            keyword in assistant_response.lower() for keyword in 
            ["booking confirmed", "successfully booked", "booking reference"]
        ):
            return BookingStage.POST_BOOKING
            
        return current_stage

chat_handlers = ChatHandlers()
