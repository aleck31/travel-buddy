import json
import boto3
from typing import List, Dict, Any, Optional
from ..core import settings, app_logger
from .tools import Tool, ToolResult


class BedrockClient:
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

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Tool]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_rag: bool = True,
        image_base64: Optional[str] = None
    ) -> str:
        """
        Generate a response using Claude via AWS Bedrock with optional RAG support
        """
        try:
            # If RAG is enabled and we have a knowledge base ID, use retrieve_and_generate
            if use_rag and self.knowledge_base_id:
                try:
                    # Get the last user message for RAG query
                    last_user_msg = next(
                        (msg['content'] for msg in reversed(messages) if msg['role'] == 'user'),
                        None
                    )
                    
                    if last_user_msg:
                        rag_response = self.agent_runtime_client.retrieve_and_generate(
                            input={
                                "text": last_user_msg
                            },
                            retrieveAndGenerateConfiguration={
                                "type": "KNOWLEDGE_BASE",
                                "knowledgeBaseConfiguration": {
                                    'knowledgeBaseId': self.knowledge_base_id,
                                    "modelArn": f"arn:aws:bedrock:us-west-2::foundation-model/{self.model_id}",
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
                    # Fall back to regular generation

            # Prepare the body for model invocation
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user" if msg["role"] == "user" else "assistant",
                        "content": msg["content"]
                    }
                    for msg in messages
                ]
            }

            # If image is provided, add it to the last user message
            if image_base64:
                if body["messages"] and body["messages"][-1]["role"] == "user":
                    body["messages"][-1]["content"] = [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": body["messages"][-1]["content"]
                        }
                    ]

            # Add tools if provided
            if tools:
                body["tools"] = [tool.model_dump() for tool in tools]

            # Invoke the model
            response = self.runtime_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )

            # Parse the response
            response_body = json.loads(response['body'].read())
            
            # Check if the response contains tool calls
            if 'tool_calls' in response_body:
                tool_results = await self.process_tool_calls(
                    response_body['tool_calls'],
                    {tool.name: tool for tool in tools} if tools else {}
                )
                # Format tool results into a response
                return self._format_tool_results(tool_results)
            
            return response_body['completion']

        except Exception as e:
            app_logger.error(f"Error generating response from Bedrock: {str(e)}")
            raise

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Format messages for Claude prompt
        """
        formatted_prompt = ""
        for message in messages:
            role = message['role']
            content = message['content']
            
            if role == "system":
                formatted_prompt += f"\n\nSystem: {content}"
            elif role == "user":
                formatted_prompt += f"\n\nHuman: {content}"
            elif role == "assistant":
                formatted_prompt += f"\n\nAssistant: {content}"
        
        formatted_prompt += "\n\nAssistant:"
        return formatted_prompt.strip()

    async def process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        available_tools: Dict[str, callable]
    ) -> List[ToolResult]:
        """
        Process tool calls from Claude's response
        """
        results = []
        for call in tool_calls:
            tool_name = call.get('name')
            tool_args = call.get('arguments', {})
            
            if tool_name in available_tools:
                try:
                    tool_func = available_tools[tool_name]
                    result = await tool_func(**tool_args)
                    results.append(result)
                except Exception as e:
                    app_logger.error(f"Error executing tool {tool_name}: {str(e)}")
                    results.append(ToolResult(
                        success=False,
                        error=f"Tool execution failed: {str(e)}"
                    ))
            else:
                results.append(ToolResult(
                    success=False,
                    error=f"Unknown tool: {tool_name}"
                ))
        
        return results

    def _format_tool_results(self, results: List[ToolResult]) -> str:
        """
        Format tool results into a response string
        """
        formatted_results = []
        for result in results:
            if result.success:
                formatted_results.append(f"Tool execution successful: {json.dumps(result.data)}")
            else:
                formatted_results.append(f"Tool execution failed: {result.error}")
        
        return "\n".join(formatted_results)


# Create a singleton instance
bedrock_client = BedrockClient()
