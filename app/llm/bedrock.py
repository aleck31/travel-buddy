import json
import boto3
from typing import List, Dict, Any, Optional
from ..core import settings, app_logger
from .tools import Tool, ToolResult


class BedrockLLM:
    """High-level interface for Bedrock LLM operations"""
    def __init__(self):
        self.client = BedrockClient()

    async def generate(
        self,        
        system_prompt: str,
        prompt_temp: str,
        context: Dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Tool]] = None,
        use_rag: Optional[bool] = False
    ) -> str:
        """
        Generate a response using the Bedrock LLM
        
        Args:
            prompt_temp: The prompt template to use
            context: Context information to inform the response
            temperature: Controls randomness in generation
            max_tokens: Maximum tokens to generate
            tools: Optional list of tools available to the model
            system_prompt: Optional system prompt to guide the model's behavior
            
        Returns:
            Generated response string
        """
        try:
            response = await self.client.generate_response(
                system_prompt=system_prompt,
                prompt_temp=prompt_temp,
                context=context,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                use_rag=use_rag
            )
            return response
        except Exception as e:
            app_logger.error(f"Error generating LLM response: {str(e)}")
            raise


class BedrockClient:
    """Low-level client for AWS Bedrock API interactions"""
    def __init__(self):
        self.runtime_client = boto3.client(
            'bedrock-runtime',
            region_name=settings.BEDROCK_REGION
        )
        
        self.agent_runtime_client = boto3.client(
            'bedrock-agent-runtime',
            region_name=settings.BEDROCK_REGION
        )
        
        self.model_id = settings.BEDROCK_MODEL_ID
        self.knowledge_base_id = settings.KNOWLEDGE_BASE_ID

    async def generate_response(
        self,
        system_prompt: str,
        prompt_temp: str,
        context: Dict[str, Any],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tools: Optional[List[Tool]] = None,
        use_rag: Optional[bool] = False,
        max_recursions: int = 5
    ) -> str:
        """Generate a response using Claude via AWS Bedrock with optional tool use"""
        try:
            # Format the initial message with proper structure
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": f"{prompt_temp}\n\nContext: {json.dumps(context)}"
                        }
                    ]
                }
            ]

            # Try RAG if enabled
            if use_rag and self.knowledge_base_id:
                rag_response = await self._try_rag_response(messages)
                if rag_response:
                    return rag_response

            # Prepare request parameters
            request_params = {
                "modelId": self.model_id,
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "stopSequences": []
                }
            }

            # Add system if provided
            if system_prompt:
                request_params["system"] = [{"text": system_prompt}]

            # Add tool configuration only if tools are provided
            if tools:
                request_params["toolConfig"] = {
                    "tools": [
                        {
                            "toolSpec": self._convert_tool_to_spec(tool)
                        } for tool in tools
                    ],
                    "toolChoice": {
                        "auto": {}
                    }
                }

            # Start conversation with Bedrock
            response = self.runtime_client.converse(**request_params)
            
            # Process the response recursively if needed
            return await self._process_response(
                response=response,
                messages=messages,
                tool_config=request_params.get("toolConfig"),
                system=request_params.get("system"),
                temperature=temperature,
                max_tokens=max_tokens,
                max_recursions=max_recursions
            )

        except Exception as e:
            app_logger.error(f"Error generating response from Bedrock: {str(e)}")
            raise

    async def _try_rag_response(self, messages: List[Dict[str, Any]]) -> Optional[str]:
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
    
    def _send_to_bedrock(
        self,
        messages: List[Dict[str, Any]],
        tool_config: Optional[Dict[str, Any]] = None,
        system: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """Send conversation to Bedrock"""
        request_params = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
                "stopSequences": []
            }
        }

        if system:
            request_params["system"] = system

        if tool_config:
            request_params["toolConfig"] = tool_config

        return self.runtime_client.converse(**request_params)

    async def _process_response(
        self,
        response: Dict[str, Any],
        messages: List[Dict[str, Any]],
        tool_config: Optional[Dict[str, Any]],
        system: Optional[List[Dict[str, str]]],
        temperature: float,
        max_tokens: int,
        max_recursions: int
    ) -> str:
        """Process Bedrock response and handle tool use recursively"""
        if max_recursions <= 0:
            raise Exception("Maximum number of tool use recursions reached")

        # Extract response content from converse API format
        output = response.get("output", {})
        message = output.get("message", {})
        message_content = message.get("content", [])
        
        # Add model's response to conversation
        messages.append({
            "role": "assistant",
            "content": message_content
        })

        # Process each content item
        response_text = ""
        tool_uses = []

        for content in message_content:
            if "text" in content:
                response_text += content["text"]
            elif "toolUse" in content:
                tool_uses.append(content["toolUse"])

        if tool_uses:
            # Handle tool uses
            tool_results = []
            
            for tool_use in tool_uses:
                result = await self._execute_tool(tool_use)
                
                tool_results.append({
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "toolUseId": tool_use["toolUseId"],
                                "content": [
                                    {
                                        "json": result.data if isinstance(result, ToolResult) and result.success else result
                                    } if not isinstance(result, dict) or "error" not in result else {
                                        "text": result["error"]
                                    }
                                ],
                                "status": "success" if (isinstance(result, ToolResult) and result.success) or (isinstance(result, dict) and "error" not in result) else "error"
                            }
                        }
                    ]
                })

            # Add tool results to conversation
            messages.extend(tool_results)

            # Continue conversation with tool results
            next_response = self._send_to_bedrock(
                messages=messages,
                tool_config=tool_config,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return await self._process_response(
                response=next_response,
                messages=messages,
                tool_config=tool_config,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                max_recursions=max_recursions - 1
            )

        # Return final response text if no tool uses
        return response_text

    async def _execute_tool(self, tool_use: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the requested tool and return results"""
        try:
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]
            
            # Get the tool function from the registered tools
            from app.llm.tools.lounge import get_available_lounges, book_lounge
            from app.llm.tools.flight import FlightTools
            from app.llm.tools.membership import check_membership_points
            
            tools = {
                "get_available_lounges": get_available_lounges,
                "book_lounge": book_lounge,
                "extract_flight_info": FlightTools().extract_flight_info,
                "check_membership_points": check_membership_points
            }
            
            if tool_name not in tools:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            # Execute the tool
            result = await tools[tool_name](**tool_input)
            
            if isinstance(result, ToolResult):
                if result.success:
                    return result.data
                else:
                    return {"error": result.error}
            else:
                return result
                
        except Exception as e:
            app_logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"error": str(e)}

    def _convert_tool_to_spec(self, tool: Tool) -> Dict[str, Any]:
        """Convert tool to Bedrock tool specification format"""
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": {
                "json": tool.parameters
            }
        }


# Create a singleton instance
bedrock_client = BedrockClient()
