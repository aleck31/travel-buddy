from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gradio.routes import mount_gradio_app

from .core import settings, app_logger
from .chatbot.chat_ui import chat_interface  # Import the specific chat_ui instance
from .services import dynamodb_service


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered airport VIP lounge booking assistant",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Gradio interface
interface = chat_interface.create_interface()

# Mount Gradio app to FastAPI
app = mount_gradio_app(app, interface, path="/")

@app.on_event("startup")
async def startup_event():
    """
    Initialize services on startup
    """
    app_logger.info(f"Starting {settings.APP_NAME}")
    
    # Initialize DynamoDB connection
    try:
        await dynamodb_service.initialize()
        app_logger.info("Successfully connected to DynamoDB table")
    except Exception as e:
        app_logger.error(f"Failed to connect to DynamoDB table: {str(e)}")
        app_logger.warning("Application starting without DynamoDB connection")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown
    """
    app_logger.info(f"Shutting down {settings.APP_NAME}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True if settings.DEBUG else False
    )
