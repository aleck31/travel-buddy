import json
import boto3
from typing import List, Dict, Any, Optional, Callable, Awaitable, Union
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
        tools: Optional[List[Dict[str, Any]]] = None,
        use_rag: Optional[bool] = False
    ) -> Union[str, Dict[str, Any]]:
        """
        Generate a response using the Bedrock LLM
        
        Args:
            prompt_temp: The prompt template to use
            context: Context information to inform the response
            temperature: Controls randomness in generation
            max_tokens: Maximum tokens to generate
            tools: Optional list of dicts containing tool spec and function
                  [{"tool": Tool, "function": Callable}]
            system_prompt: Optional system prompt to guide the model's behavior
            
        Returns:
            Either a string response or a dict containing response and tool results
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
        tools: Optional[List[Dict[str, Any]]] = None,
        use_rag: Optional[bool] = False,
        max_recursions: int = 5
    ) -> Union[str, Dict[str, Any]]:
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
                            "toolSpec": self._convert_tool_to_spec(tool["tool"])
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
                tools=tools,
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
        tools: Optional[List[Dict[str, Any]]],
        system: Optional[List[Dict[str, str]]],
        temperature: float,
        max_tokens: int,
        max_recursions: int
    ) -> Union[str, Dict[str, Any]]:
        """Process Bedrock response and handle tool use recursively"""
        if max_recursions <= 0:
            raise Exception("Maximum number of tool use recursions reached")

        # Extract response content from converse API format
        output = response.get("output", {})
        message = output.get("message", {})
        message_content = message.get("content", [])
        stop_reason = response.get("stopReason")
        
        # Add model's response to conversation
        messages.append({
            "role": "assistant",
            "content": message_content
        })

        # Process each content item
        response_text = ""
        tool_uses = []
        state_updates = {}

        for content in message_content:
            if isinstance(content, dict):
                if "text" in content:
                    response_text += content["text"]
                elif "toolUse" in content:
                    tool_use = content["toolUse"]
                    if isinstance(tool_use, dict) and "name" in tool_use:
                        tool_uses.append(tool_use)

        # If stop reason is tool_use, execute tools and continue conversation
        if stop_reason == "tool_use" and tool_uses and tools:
            tool_results_messages = []
            
            for tool_use in tool_uses:
                app_logger.info(f"Use tool: {tool_use.get('name')}")
                result = await self._execute_tool(tool_use, tools)
                app_logger.info(f"{tool_use.get('name')} finished successful: {result.success}")
                
                # Get state updates from tool result
                if result.success:
                    tool_state = result.get_state_update()
                    app_logger.info(f"Tool state update: {json.dumps(tool_state)}")
                    state_updates.update(tool_state)
                
                tool_results_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "toolUseId": tool_use.get("toolUseId", ""),
                                "content": [{"json": result.data if result.success else {"error": result.error}}],
                                "status": "success" if result.success else "error"
                            }
                        }
                    ]
                })

            # Add tool results to conversation
            messages.extend(tool_results_messages)

            # Continue conversation with tool results
            next_response = self._send_to_bedrock(
                messages=messages,
                tool_config=tool_config,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            final_response = await self._process_response(
                response=next_response,
                messages=messages,
                tool_config=tool_config,
                tools=tools,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                max_recursions=max_recursions - 1
            )

            # If state updates exist, return both response and state
            if state_updates:
                if isinstance(final_response, str):
                    return {
                        "response": final_response,
                        "state": state_updates
                    }
                elif isinstance(final_response, dict):
                    if "state" in final_response:
                        final_response["state"].update(state_updates)
                    else:
                        final_response["state"] = state_updates
                    return final_response

            return final_response

        # Return final response text if no tool uses or end_turn
        return response_text

    async def _execute_tool(
        self, 
        tool_use: Dict[str, Any], 
        tools: List[Dict[str, Any]]
    ) -> ToolResult:
        """Execute the requested tool and return results"""
        try:
            tool_name = tool_use.get("name")
            if not tool_name:
                return ToolResult(success=False, error="Tool name not provided")
                
            tool_input = tool_use.get("input", {})
            
            # Find the tool function from the provided tools list
            tool_func = next(
                (t["function"] for t in tools if t["tool"].name == tool_name),
                None
            )
            
            if not tool_func:
                return ToolResult(success=False, error=f"Unknown tool: {tool_name}")
            
            # Execute the tool
            result = await tool_func(**tool_input)
            
            if isinstance(result, ToolResult):
                return result
            else:
                # Convert non-ToolResult to ToolResult
                return ToolResult(success=True, data=result)
                
        except Exception as e:
            app_logger.error(f"Error executing tool {tool_name if 'tool_name' in locals() else 'unknown'}: {str(e)}")
            return ToolResult(
                success=False, 
                error=f"Error executing tool {tool_name if 'tool_name' in locals() else 'unknown'}: {str(e)}"
            )

    def _convert_tool_to_spec(self, tool: Tool) -> Dict[str, Any]:
        """Convert tool to Bedrock tool specification format"""
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": {
                "json": {
                    **tool.parameters,
                    "required": tool.required
                }
            }
        }


# Create a singleton instance
bedrock_client = BedrockClient()
