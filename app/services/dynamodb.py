import boto3
from typing import Dict, Any, Optional, List
from ..core import settings, app_logger


class DynamoDBService:
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.table_name = settings.DYNAMODB_TABLE_NAME
        self.table = None

    async def initialize(self) -> bool:
        """
        Initialize connection to DynamoDB table
        """
        try:
            self.table = self.dynamodb.Table(self.table_name)
            # Verify table exists by making a simple DescribeTable call
            self.table.load()
            app_logger.info(f"Connected to DynamoDB table: {self.table_name}")
            return True
        except Exception as e:
            app_logger.error(f"Error connecting to DynamoDB table: {str(e)}")
            raise

    async def put_item(self, item: Dict[str, Any]) -> bool:
        """
        Put an item into the DynamoDB table
        """
        try:
            if not self.table:
                await self.initialize()
            
            self.table.put_item(Item=item)
            return True
        except Exception as e:
            app_logger.error(f"Error putting item to DynamoDB: {str(e)}")
            return False

    async def get_item(
        self,
        partition_key: str,
        sort_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get an item from the DynamoDB table
        """
        try:
            if not self.table:
                await self.initialize()
            
            response = self.table.get_item(
                Key={
                    'pk': partition_key,
                    'sk': sort_key
                }
            )
            return response.get('Item')
        except Exception as e:
            app_logger.error(f"Error getting item from DynamoDB: {str(e)}")
            return None

    async def query_items(
        self,
        partition_key: str,
        sort_key_prefix: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query items from the DynamoDB table
        """
        try:
            if not self.table:
                await self.initialize()
            
            if sort_key_prefix:
                response = self.table.query(
                    KeyConditionExpression=(
                        'pk = :pk AND begins_with(sk, :sk_prefix)'
                    ),
                    ExpressionAttributeValues={
                        ':pk': partition_key,
                        ':sk_prefix': sort_key_prefix
                    }
                )
            else:
                response = self.table.query(
                    KeyConditionExpression='pk = :pk',
                    ExpressionAttributeValues={
                        ':pk': partition_key
                    }
                )
            
            return response.get('Items', [])
        except Exception as e:
            app_logger.error(f"Error querying items from DynamoDB: {str(e)}")
            return []


# Create a singleton instance
dynamodb_service = DynamoDBService()
