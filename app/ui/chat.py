import gradio as gr
from typing import List, Tuple, Optional
from datetime import datetime
import uuid
import base64
from pathlib import Path

from ..core import app_logger
from ..models.chat import ChatSession, ChatMessage, MessageRole
from ..llm import bedrock_client, LLMTools, AVAILABLE_TOOLS
from ..services.dynamodb import dynamodb_service


class ChatUI:
    def __init__(self):
        self.tools = LLMTools()
        self.active_sessions: dict = {}  # Store active chat sessions
        self.system_prompt = """
            You are 'Travel Buddy', an AI assistant specialized in helping users book 
            airport VIP lounges. Use the knowledge base to provide accurate information 
            about lounges and guide users through the booking process. Be friendly and 
            professional while maintaining a helpful demeanor.
        """

    def create_interface(self) -> gr.Blocks:
        """
        Create the Gradio chat interface
        """
        with gr.Blocks(title="Travel Buddy - Airport Lounge Assistant") as interface:
            with gr.Row():
                gr.Markdown(
                    """
                    # ✈️ Travel Buddy
                    Your AI assistant for booking airport VIP lounges
                    """
                )

            with gr.Row():
                with gr.Column(scale=4):
                    chatbot = gr.Chatbot(
                        [],
                        elem_id="chatbot",
                        bubble_full_width=False,
                        avatar_images=(None, "🤖"),
                        height=600,
                        type="messages"  # Use OpenAI-style message format
                    )
                    with gr.Row():
                        msg = gr.Textbox(
                            show_label=False,
                            placeholder="Type your message here...",
                            container=False
                        )
                        submit_btn = gr.Button("Send", variant="primary")

                    with gr.Row():
                        clear_btn = gr.Button("Clear Chat")
                        upload_btn = gr.UploadButton(
                            "📎 Upload Flight Document",
                            file_types=["image"]  # Restrict to images for OCR
                        )

                with gr.Column(scale=1):
                    with gr.Accordion("Session Info", open=False):
                        user_id = gr.Textbox(
                            label="User ID",
                            value="demo1",  # Demo user ID
                            interactive=True
                        )
                        points_display = gr.Markdown(
                            "Available Points: Checking..."
                        )
                        with gr.Row():
                            refresh_points_btn = gr.Button("🔄 Refresh Points")

            # Event handlers
            submit_btn.click(
                self._handle_message,
                inputs=[msg, chatbot, user_id],
                outputs=[msg, chatbot, points_display]
            )
            msg.submit(
                self._handle_message,
                inputs=[msg, chatbot, user_id],
                outputs=[msg, chatbot, points_display]
            )
            clear_btn.click(
                self._clear_chat,
                inputs=[user_id],
                outputs=[chatbot, points_display]
            )
            upload_btn.upload(
                self._handle_upload,
                inputs=[upload_btn, chatbot, user_id],
                outputs=[chatbot, points_display]
            )
            refresh_points_btn.click(
                self._refresh_points,
                inputs=[user_id],
                outputs=[points_display]
            )

        return interface

    async def _handle_message(
        self,
        message: str,
        history: List[dict],
        user_id: str
    ) -> Tuple[str, List[dict], str]:
        """
        Handle incoming chat messages
        """
        if not message.strip():
            return "", history, await self._get_points_display(user_id)

        try:
            # Get or create session
            session = await self._get_or_create_session(user_id)
            
            # Add user message to session
            user_message = ChatMessage(role=MessageRole.USER, content=message)
            session.messages.append(user_message)

            # Generate response using Claude with RAG
            try:
                response = await bedrock_client.generate_response(
                    messages=[msg.model_dump() for msg in session.messages],
                    tools=AVAILABLE_TOOLS,
                    use_rag=True  # Enable RAG for lounge information
                )
            except Exception as e:
                app_logger.error(f"Error generating response: {str(e)}")
                response = (
                    "I apologize, but I'm having trouble processing your request. "
                    "Please try again in a moment."
                )

            # Add assistant response to session
            assistant_message = ChatMessage(role=MessageRole.ASSISTANT, content=response)
            session.messages.append(assistant_message)

            # Save messages to DynamoDB
            await self._save_messages(session, [user_message, assistant_message])

            # Update chat history
            history.extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": response}
            ])
            
            # Update points display
            points_display = await self._get_points_display(user_id)
            
            return "", history, points_display

        except Exception as e:
            app_logger.error(f"Error handling message: {str(e)}")
            error_msg = (
                "I apologize, but I encountered an error processing your request. "
                "Please try again."
            )
            history.append({"role": "assistant", "content": error_msg})
            return "", history, await self._get_points_display(user_id)

    async def _handle_upload(
        self,
        file: gr.File,
        history: List[dict],
        user_id: str
    ) -> Tuple[List[dict], str]:
        """
        Handle uploaded flight documents with OCR processing
        """
        try:
            # Read and encode the image file
            image_path = Path(file.name)
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Get or create session
            session = await self._get_or_create_session(user_id)

            # Add upload message to history
            upload_message = (
                "I've uploaded a flight ticket image. Please analyze it and extract "
                "the relevant information such as flight number, date, and passenger details."
            )
            user_message = ChatMessage(role=MessageRole.USER, content=upload_message)
            session.messages.append(user_message)

            # Generate response using Claude with image processing
            try:
                response = await bedrock_client.generate_response(
                    messages=[msg.model_dump() for msg in session.messages],
                    tools=AVAILABLE_TOOLS,
                    use_rag=True,
                    image_base64=image_base64
                )
            except Exception as e:
                app_logger.error(f"Error processing image: {str(e)}")
                response = (
                    "I apologize, but I'm having trouble processing the uploaded image. "
                    "Please ensure it's a clear photo of your flight ticket and try again."
                )

            # Add assistant response to session
            assistant_message = ChatMessage(role=MessageRole.ASSISTANT, content=response)
            session.messages.append(assistant_message)

            # Save messages to DynamoDB
            await self._save_messages(session, [user_message, assistant_message])

            # Update chat history
            history.extend([
                {"role": "user", "content": f"[Uploaded flight ticket image]"},
                {"role": "assistant", "content": response}
            ])

            # Update points display
            points_display = await self._get_points_display(user_id)
            
            return history, points_display

        except Exception as e:
            app_logger.error(f"Error handling file upload: {str(e)}")
            error_msg = (
                "I apologize, but I couldn't process your uploaded file. "
                "Please ensure it's a valid image file and try again."
            )
            history.extend([
                {"role": "user", "content": f"[Upload failed: {file.name}]"},
                {"role": "assistant", "content": error_msg}
            ])
            return history, await self._get_points_display(user_id)

    async def _clear_chat(self, user_id: str) -> Tuple[List[dict], str]:
        """
        Clear the chat history and create a new session
        """
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
        return [], "Available Points: Checking..."

    async def _refresh_points(self, user_id: str) -> str:
        """
        Refresh user's points display
        """
        return await self._get_points_display(user_id)

    async def _get_or_create_session(self, user_id: str) -> ChatSession:
        """
        Get existing chat session or create a new one
        """
        if user_id not in self.active_sessions:
            # Try to load existing session from DynamoDB
            session_data = await self._load_latest_session(user_id)
            
            if session_data:
                session = ChatSession.from_dynamodb(session_data)
            else:
                # Create new session if none exists
                session = ChatSession(
                    session_id=str(uuid.uuid4()),
                    user_id=user_id,
                    messages=[
                        ChatMessage(
                            role=MessageRole.SYSTEM,
                            content=self.system_prompt
                        )
                    ]
                )
                # Save new session to DynamoDB
                await self._save_session(session)
            
            self.active_sessions[user_id] = session
            
        return self.active_sessions[user_id]

    async def _get_points_display(self, user_id: str) -> str:
        """
        Get user's points display
        """
        try:
            result = await self.tools.check_membership_points(user_id)
            if result.success:
                points = result.data["points"]
                return f"Available Points: {points}"
            return "Available Points: Error checking points"
        except Exception as e:
            app_logger.error(f"Error checking points: {str(e)}")
            return "Available Points: Error checking points"

    async def _save_session(self, session: ChatSession):
        """
        Save chat session to DynamoDB
        """
        try:
            item = {
                'pk': f"USER#{session.user_id}",
                'sk': f"SESSION#{session.session_id}",
                'type': 'CHAT_SESSION',
                'user_id': session.user_id,
                'session_id': session.session_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'messages': [msg.model_dump() for msg in session.messages]
            }
            await dynamodb_service.put_item(item)
        except Exception as e:
            app_logger.error(f"Error saving session to DynamoDB: {str(e)}")

    async def _save_messages(self, session: ChatSession, messages: List[ChatMessage]):
        """
        Save chat messages to DynamoDB
        """
        try:
            # Update the session with new messages
            item = {
                'pk': f"USER#{session.user_id}",
                'sk': f"SESSION#{session.session_id}",
                'type': 'CHAT_SESSION',
                'user_id': session.user_id,
                'session_id': session.session_id,
                'updated_at': datetime.now().isoformat(),
                'messages': [msg.model_dump() for msg in session.messages]
            }
            await dynamodb_service.put_item(item)
        except Exception as e:
            app_logger.error(f"Error saving messages to DynamoDB: {str(e)}")

    async def _load_latest_session(self, user_id: str) -> Optional[dict]:
        """
        Load the latest chat session for a user from DynamoDB
        """
        try:
            # Query for sessions belonging to the user
            sessions = await dynamodb_service.query_items(
                partition_key=f"USER#{user_id}",
                sort_key_prefix="SESSION#"
            )
            
            if sessions:
                # Return the most recent session based on updated_at
                return max(sessions, key=lambda x: x.get('updated_at', ''))
            return None
        except Exception as e:
            app_logger.error(f"Error loading session from DynamoDB: {str(e)}")
            return None


# Create a singleton instance
chat_ui = ChatUI()
