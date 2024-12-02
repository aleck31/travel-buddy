import asyncio
import boto3
from datetime import datetime
from app.core import settings


def list_chat_sessions(user_id: str = "demo1"):
    """List all chat sessions for a user from DynamoDB"""
    try:
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=settings.AWS_REGION
        )
        
        # Get the table
        table = dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
        
        # Query for user's sessions
        response = table.query(
            KeyConditionExpression='pk = :pk AND begins_with(sk, :sk_prefix)',
            ExpressionAttributeValues={
                ':pk': f"USER#{user_id}",
                ':sk_prefix': "SESSION#"
            }
        )
        
        # Print sessions
        print(f"\nChat sessions for user {user_id}:")
        for item in response.get('Items', []):
            print(f"\nSession ID: {item['session_id']}")
            print(f"Updated at: {item['updated_at']}")
            print("\nMessages:")
            for msg in item.get('messages', []):
                print(f"{msg['role']}: {msg['content'][:100]}...")
            print("-" * 80)
            
        return response.get('Items', [])
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

if __name__ == "__main__":
    # List chat sessions for demo1 user
    sessions = list_chat_sessions("demo1")
    if not sessions:
        print("No chat sessions found for demo1")
