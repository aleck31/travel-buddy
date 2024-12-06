"""
Travel Buddy Chat Interface
This module provides the main entry point for the chat interface.
"""
import gradio as gr
from pathlib import Path
from typing import Tuple, Dict

from .handlers.chat_handlers import chat_handlers

class ChatInterface:
    def __init__(self):
        self.interface = None

    def create_interface(self) -> gr.Blocks:
        """Create the Gradio chat interface"""
        with gr.Blocks(title="Travel Buddy - Airport Lounge Assistant") as interface:
            # Welcome dialog components
            welcome_container = gr.Column()
            with welcome_container:
                gr.Markdown(
                    """
                    # ✈️ Welcome to Travel Buddy
                    Please enter your information to begin
                    """
                )
                welcome_user_id = gr.Textbox(
                    label="User ID",
                    placeholder="Enter your user ID",
                    value="test_user_1"
                )
                welcome_service = gr.Dropdown(
                    choices=["Choose...", "Lounge", "Restaurant", "Limousine", "Gifts"],
                    label="Select Service",
                    value="Choose..."
                )
                welcome_error = gr.Markdown(visible=True)
                start_btn = gr.Button("Start Chat", variant="primary")

            # Main chat interface (initially hidden)
            main_container = gr.Column(visible=False)
            with main_container:
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
                            avatar_images=[str(Path(__file__).parent / "avata_user.jpg"), str(Path(__file__).parent / "avata_buddy.jpg")],
                            height=600,
                            type="messages"
                        )
                        with gr.Row():
                            with gr.Column(scale=2):
                                msg = gr.Textbox(
                                    show_label=False,
                                    placeholder="Type your message here...",
                                    container=False
                                )
                            with gr.Column(scale=1):
                                submit_btn = gr.Button("Send", variant="primary")

                        with gr.Row():
                            upload_btn = gr.UploadButton(
                                "📎 Upload Flight Document",
                                file_types=["image"]
                            )
                            gr.Button("🎧 Call customer service")
                            clear_btn = gr.Button("Clear Chat")

                    with gr.Column(scale=1):
                        with gr.Accordion("Session Info", open=False):
                            user_id = gr.Textbox(
                                label="User ID",
                                interactive=False
                            )
                            service = gr.Dropdown(
                                choices=["Lounge", "Restaurant", "Limousine", "Gifts"],
                                label="Service",
                                interactive=False
                            )
                            profile_display = gr.Markdown(
                                "User Profile: Loading..."
                            )
                            points_display = gr.Markdown(
                                "Available Points: Checking..."
                            )
                            with gr.Row():
                                refresh_btn = gr.Button("🔄 Refresh Info")

                        # Service Progress Section
                        with gr.Accordion("Service Progress", open=True):
                            service_choose = gr.Dropdown(
                                choices=["Lounge", "Restaurant", "Limousine", "Gifts"],
                                show_label=False,
                                value="Lounge",
                                interactive=False
                            )                            
                            gr.Markdown("### Current Stage:")
                            current_stage = gr.Markdown(
                                value='Initial Engagement'
                            )
                            progress_bar = gr.Slider(
                                minimum=0,
                                maximum=6,
                                value=0,
                                label="Overall Progress",
                                interactive=False
                            )

            def update_visibility(user_id: str, service: str) -> Tuple[Dict, Dict]:
                if service == "Choose...":
                    return (
                        gr.update(visible=True),
                        gr.update(visible=False)
                    )
                return (
                    gr.update(visible=False),
                    gr.update(visible=True)
                )

            # Event handlers
            start_btn.click(
                chat_handlers.handle_start_chat,
                inputs=[welcome_user_id, welcome_service],
                outputs=[
                    user_id,
                    service,
                    chatbot,
                    points_display,
                    profile_display,
                    welcome_error,
                    current_stage,
                    progress_bar
                ]
            ).then(
                update_visibility,
                inputs=[welcome_user_id, welcome_service],
                outputs=[welcome_container, main_container]
            )

            submit_btn.click(
                chat_handlers.handle_message,
                inputs=[msg, chatbot, user_id, service],
                outputs=[msg, chatbot, points_display, profile_display, current_stage, progress_bar]
            )

            msg.submit(
                chat_handlers.handle_message,
                inputs=[msg, chatbot, user_id, service],
                outputs=[msg, chatbot, points_display, profile_display, current_stage, progress_bar]
            )

            clear_btn.click(
                chat_handlers.handle_clear_chat,
                inputs=[user_id],
                outputs=[chatbot, points_display, profile_display, current_stage, progress_bar]
            )

            upload_btn.upload(
                chat_handlers.handle_upload,
                inputs=[upload_btn, chatbot, user_id, service],
                outputs=[chatbot, points_display, profile_display, current_stage, progress_bar]
            )

            refresh_btn.click(
                chat_handlers.handle_refresh_info,
                inputs=[user_id],
                outputs=[points_display, profile_display]
            )

            self.interface = interface
            return interface
        
# Create a singleton instance
chat_interface = ChatInterface()
