import json
import boto3
from typing import List, Dict, Any, Optional, Generator
from ..core import settings, app_logger
from .tools import Tool, ToolResult


class BedrockLLM:
    """High-level interface for Bedrock LLM operations"""
    def __init__(self):
        self.client = BedrockClient()

    # Note: generate() will be deprecated, it's recommended to use stream_generate() method with higher priority
    async def generate(
        self,
        prompt: str,
        context: Dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate a response using the Bedrock LLM
        
        Args:
            prompt: The prompt template to use
            context: Context information to inform the response
            temperature: Controls randomness in generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response string
        """
        # Format messages for the model
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": f"{prompt}\n\nContext: {json.dumps(context)}"}]
            }
        ]
        
        try:
            response = self.client.generate_response(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response
        except Exception as e:
            app_logger.error(f"Error generating LLM response: {str(e)}")
            raise

    def stream_generate(
        self,
        prompt: str,
        context: Dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response using the Bedrock LLM
        
        Args:
            prompt: The prompt template to use
            context: Context information to inform the response
            temperature: Controls randomness in generation
            max_tokens: Maximum tokens to generate
            
        Yields:
            Generated response chunks as they become available
        """
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": f"{prompt}\n\nContext: {json.dumps(context)}"}]
            }
        ]
        
        try:
            # Prepare request body
            body = self.client._prepare_request_body(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            # Start streaming conversation
            stream = self.client.runtime_client.invoke_model_with_response_stream(
                modelId=self.client.model_id,
                body=json.dumps(body)
            )

            # Process streaming response
            for event in stream['body']:
                if 'chunk' in event:
                    chunk_data = json.loads(event['chunk']['bytes'].decode())
                    if 'content' in chunk_data and len(chunk_data['content']) > 0:
                        yield chunk_data['content'][0]['text']

        except Exception as e:
            app_logger.error(f"Error generating streaming LLM response: {str(e)}")
            raise


class BedrockClient:
    """Low-level client for AWS Bedrock API interactions"""
    def __init__(self):
        # Initialize Bedrock runtime client for model invocation
        self.runtime_client = boto3.client(
            'bedrock-runtime',
            region_name=settings.BEDROCK_REGION
        )
        
        # Initialize Bedrock agent runtime client for RAG operations
        self.agent_runtime_client = boto3.client(
            'bedrock-agent-runtime',
            region_name=settings.BEDROCK_REGION
        )
        
        self.model_id = settings.BEDROCK_MODEL_ID
        self.knowledge_base_id = settings.KNOWLEDGE_BASE_ID

    def generate_response(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Tool]] = None,
        image_base64: Optional[str] = None,
        use_rag: bool = True
    ) -> str:
        """
        Generate a response using Claude via AWS Bedrock with optional RAG support
        """
        try:
            # Try RAG if enabled
            if use_rag and self.knowledge_base_id:
                rag_response = self._try_rag_response(messages)
                if rag_response:
                    return rag_response

            # Prepare request body
            body = self._prepare_request_body(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                image_base64=image_base64
            )

            # Invoke the model
            response = self.runtime_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )

            # Parse and return the response
            return self._parse_response(response)

        except Exception as e:
            app_logger.error(f"Error generating response from Bedrock: {str(e)}")
            raise

    def _try_rag_response(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """Try to get a response using RAG if possible"""
        try:
            # Get the last user message for RAG query
            last_user_msg = next(
                (msg['content'][0]['text'] for msg in reversed(messages) if msg['role'] == 'user'),
                None
            )
            
            if last_user_msg:
                # Construct the model ARN using the region and model ID
                model_arn = f"arn:aws:bedrock:{settings.BEDROCK_REGION}::foundation-model/{self.model_id}"
                
                rag_response = self.agent_runtime_client.retrieve_and_generate(
                    input={
                        "text": last_user_msg
                    },
                    retrieveAndGenerateConfiguration={
                        "type": "KNOWLEDGE_BASE",
                        "knowledgeBaseConfiguration": {
                            'knowledgeBaseId': self.knowledge_base_id,
                            "modelArn": model_arn,
                            "retrievalConfiguration": {
                                "vectorSearchConfiguration": {
                                    "numberOfResults": 3
                                }
                            }
                        }
                    }
                )
                
                if 'output' in rag_response and 'text' in rag_response['output']:
                    return rag_response['output']['text']
                    
        except Exception as e:
            app_logger.error(f"Error retrieving from knowledge base: {str(e)}")
            
        return None

    def _prepare_request_body(
        self,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Tool]] = None,
        image_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare the request body for model invocation"""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }

        # Add image if provided
        if image_base64 and body["messages"]:
            self._add_image_to_message(body["messages"][-1], image_base64)

        # Add tools if provided
        if tools:
            body["tools"] = [tool.model_dump() for tool in tools]

        return body

    def _add_image_to_message(self, message: Dict[str, Any], image_base64: str) -> None:
        """Add image content to a message"""
        if message["role"] == "user":
            message["content"].insert(0, {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64
                }
            })

    def _parse_response(self, response: Any) -> str:
        """Parse the response from Bedrock"""
        response_body = json.loads(response['body'].read())
        
        if 'content' in response_body and len(response_body['content']) > 0:
            return response_body['content'][0]['text']
        elif 'messages' in response_body and len(response_body['messages']) > 0:
            return response_body['messages'][-1]['content'][0]['text']
        else:
            app_logger.error(f"Unexpected response format: {response_body}")
            raise ValueError("Unexpected response format from Bedrock")


# Create a singleton instance
bedrock_client = BedrockClient()
