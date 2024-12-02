# Travel Buddy

A GenAI-powered airport VIP lounge booking assistant using AWS Bedrock (Claude) and FastAPI.

## Overview

Travel Buddy provides a friendly chatbot interface for credit card customers to book airport VIP lounges. The application uses Claude (via AWS Bedrock) to process natural language requests and guide users through the booking process.

## Features

### MVP Features
- Chat interface for lounge booking requests
- Basic lounge recommendations
- Booking confirmation flow
- OCR for flight document verification
- RAG-based lounge knowledge base
- Mock membership points system
- Mock flight information verification

### Future Enhancements
- Integration with real membership system
- Weather information integration
- SMS notifications

## Tech Stack

- **Backend Framework**: FastAPI
- **UI Framework**: Gradio
- **AI Model**: Claude 3.5 Sonnet v2 (AWS Bedrock)
- **Database**: AWS DynamoDB
- **Additional Services**:
  - AWS Bedrock Knowledge Base (RAG)
  - Amazon Textract (OCR)

## Project Structure

```
travel-buddy/
├── app/                 # Main application package
│   ├── main.py         # FastAPI application entry point
│   ├── core/           # Core configuration
│   │   ├── config.py   # Configuration settings
│   │   └── logging.py  # Unified log configuration
│   ├── models/         # Data models and schemas
│   ├── llm/           # Large language model functions
│   │   ├── bedrock.py   # Bedrock Client
│   │   └── tools.py   # Tools for LLM
│   ├── services/       # Business logic and external services
│   ├── api/           # API routes
│   ├── ui/            # Gradio UI
│   └── utils/         # Helper functions
├── logs/              # Application logs
└── requirements.txt   # Project dependencies
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
# AWS Credentials (required for AWS services)
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=your_region
```

3. Run the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

4. Access the application:
- Open your browser and navigate to `http://localhost:8080`
- The chat interface will be available on the main page

## Usage

1. **Starting a Chat Session**
   - Enter your user ID (default: demo1)
   - Your available points will be displayed in the sidebar

2. **Booking a Lounge**
   - Start by telling Travel Buddy about your travel plans
   - Provide flight details when requested
   - Upload flight documents if needed (OCR verification)
   - Choose from recommended lounges based on your preferences

3. **Managing Your Booking**
   - View booking confirmation details
   - Check your remaining points
   - Clear chat history to start a new session

## Development

- The application uses FastAPI for the backend and Gradio for the UI
- AWS Bedrock is used for both the LLM (Claude) and RAG capabilities
- The MVP uses mock implementations for some services (membership, flight verification)
- Logs are stored in the `logs` directory

## Error Handling

The application includes comprehensive error handling:
- AWS service connection issues
- LLM response generation failures
- File upload problems
- Points checking errors

All errors are logged and user-friendly error messages are displayed in the chat interface.

## Security Notes

- AWS credentials should be properly secured and never committed to version control
- Use environment variables for all sensitive configuration
- The application includes CORS middleware for API security
