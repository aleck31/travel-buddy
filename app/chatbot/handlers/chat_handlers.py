# chat_handlers.py handles UI/API level interactions
from typing import List, Tuple
from datetime import datetime
import logging
import re
import json

from ...core import app_logger
from ...models.chat import ChatMessage, MessageRole, BookingStage
from ..session_service import session_service
from ..data_service import data_service
from third_party.membership.service import membership_service
from app.llm.bedrock import BedrockLLM


class ChatHandlers:
    def __init__(self):
        self.llm = BedrockLLM()

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
            
            # Create context for LLM
            context = {
                "user_profile": {
                    "first_name": profile.first_name,
                    "last_name": profile.last_name,
                    "gender": profile.gender,
                    "preferred_language": profile.preferred_language,
                    "points": profile.points
                },
                "service": f'{service} booking',
                "current_stage": BookingStage.INITIAL_ENGAGEMENT.value,
                "session_state": {                    
                    "stage_data": session.stage_data.model_dump() if session.stage_data else None,
                    "is_new_session": True
                }
            }

            # greeting to LLM
            prompt_template=f"It is {datetime.now()} at this moment, let's begin our conversation. Please note to follow the INTERACTION GUIDELINES."
            
            with open("app/llm/prompts/travel_buddy_prompt.txt", "r") as f:
                system_prompt = f.read()

            # Create instance of BedrockLLM for static method
            llm = BedrockLLM()
            
            # Use converse API for greeting - no tools needed for initial greeting
            response = await llm.generate(
                prompt_temp=prompt_template,
                system_prompt=system_prompt,
                context=context,
                temperature=0.7,
                max_tokens=200,  # Shorter response for greeting
                # No tools needed for greeting
            )
            
            # Extract greeting text from response
            greeting = response if isinstance(response, str) else response.get("response", "")
            
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
            stage = session.current_stage
            return "", history, points_display, profile_display, stage.value, BookingStage.get_stage_number(stage)

        try:
            session = await session_service.get_or_create_session(user_id)
            app_logger.info(f"Processing message in stage: {session.current_stage.value}")
            
            # Process message and get response
            result = await session_service.process_message(
                session=session,
                user_id=user_id,
                message=message,
                service=service
            )

            # Log state updates if any
            if "state" in result:
                app_logger.info(f"Message processing resulted in state update: {json.dumps(result['state'])}")

            # Update chat history
            history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": result["response"]}
            ])
            
            # Save messages to session
            user_message = ChatMessage(role=MessageRole.USER, content=message)
            assistant_message = ChatMessage(role=MessageRole.ASSISTANT, content=result["response"])
            session.messages.extend([user_message, assistant_message])
            await session_service.save_messages(session, [user_message, assistant_message])
            
            # Get updated displays
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            
            # Return current stage info
            stage = session.current_stage
            app_logger.info(f"Stage after message processing: {stage.value}")
            return "", history, points_display, profile_display, stage.value, BookingStage.get_stage_number(stage)

        except Exception as e:
            app_logger.error(f"Error handling message: {str(e)}")
            error_msg = "I apologize, but I encountered an error processing your request. Please try again."
            history.append({"role": "assistant", "content": error_msg})
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            session = await session_service.get_or_create_session(user_id)
            stage = session.current_stage
            return "", history, points_display, profile_display, stage.value, BookingStage.get_stage_number(stage)

    @staticmethod
    async def handle_upload(
        file_path: str,  # Gradio UploadButton returns a file path as string
        history: List[dict],
        user_id: str,
        service: str
    ) -> Tuple[List[dict], str, str, str, int]:
        """Handle uploaded flight documents"""
        try:
            session = await session_service.get_or_create_session(user_id)
            app_logger.info(f"Processing file upload in stage: {session.current_stage.value}")
            
            # Process the upload through session service using the file path directly
            result = await session_service.process_message(
                session=session,
                user_id=user_id,
                message=file_path,
                service=service,
                image_path=file_path  # Use the file path directly
            )

            # Log state updates if any
            if "state" in result:
                app_logger.info(f"File upload processing resulted in state update: {json.dumps(result['state'])}")

            # Update chat history
            history.extend([
                {"role": "user", "content": (file_path,)},  # Tuple format for image display
                {"role": "assistant", "content": result["response"]}
            ])

            # Save messages to session
            user_message = ChatMessage(
                role=MessageRole.USER,
                # Mark real file path
                content="[Uploaded a boarding pass or flight ticket picture]"
            )
            assistant_message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=result["response"]
            )
            session.messages.extend([user_message, assistant_message])
            await session_service.save_messages(session, [user_message, assistant_message])

            # Get updated displays
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            
            # Return current stage info
            stage = session.current_stage
            app_logger.info(f"Stage after file upload processing: {stage.value}")
            return history, points_display, profile_display, stage.value, BookingStage.get_stage_number(stage)

        except Exception as e:
            app_logger.error(f"Error handling file upload: {str(e)}")
            error_msg = "I apologize, but I couldn't process your uploaded file. Please ensure it's a valid image file and try again."
            history.extend([
                {"role": "user", "content": f"[Upload failed: {file_path}]"},
                {"role": "assistant", "content": error_msg}
            ])
            points_display = await data_service.get_points_display(user_id)
            profile_display = await data_service.get_profile_display(user_id)
            session = await session_service.get_or_create_session(user_id)
            stage = session.current_stage
            return history, points_display, profile_display, stage.value, BookingStage.get_stage_number(stage)

    @staticmethod
    async def handle_clear_chat(user_id: str) -> Tuple[List[dict], str, str, str, int]:
        """Clear the chat history and create a new session"""
        await session_service.clear_session(user_id)
        session = await session_service.get_or_create_session(user_id)
        points_display = await data_service.get_points_display(user_id)
        profile_display = await data_service.get_profile_display(user_id)
        stage = session.current_stage
        return [], points_display, profile_display, stage.value, BookingStage.get_stage_number(stage)

    @staticmethod
    async def handle_refresh_info(user_id: str) -> Tuple[str, str]:
        """Refresh user's points and profile display"""
        points_display = await data_service.get_points_display(user_id)
        profile_display = await data_service.get_profile_display(user_id)
        return points_display, profile_display

chat_handlers = ChatHandlers()
