from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Travel Buddy"
    DEBUG: bool = False
    
    # AWS Settings
    AWS_REGION: str = "ap-southeast-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # Bedrock Settings
    BEDROCK_REGION: str = "us-west-2"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # RAG Settings
    KNOWLEDGE_BASE_ID: str = "OYWXI5HX47"
    
    # DynamoDB Settings
    DYNAMODB_TABLE_NAME: str = "travel_buddy_db"
    
    # Textract File Upload Settings
    MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB
    SUPPORTED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Create and cache settings instance.
    Settings are loaded from environment variables and .env file.
    Environment variables take precedence over .env file values.
    """
    return Settings()


# Create settings instance
settings = get_settings()
