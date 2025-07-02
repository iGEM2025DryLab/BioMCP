import json
import openai
from typing import List, Dict, Any, AsyncIterator
from bio_mcp_host.llm_clients.base import BaseLLMClient, Message, LLMResponse, LLMConfig

class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client"""
    
    def __init__(self, config: LLMConfig, mcp_client=None):
        super().__init__(config, mcp_client)
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
        
        # Latest models (2025)
        self.available_models = [
            "gpt-4.1",           # Latest GPT-4.1 (2025)
            "gpt-4.1-mini",      # Lightweight version
            "gpt-4.1-nano",      # OpenAI's first nano model
            "gpt-4o",            # GPT-4 Omni model
            "gpt-4-turbo",       # Turbo version
            "gpt-4",             # Standard GPT-4
            "gpt-3.5-turbo"      # Legacy model
        ]
    
    async def chat_completion(self, 
                            messages: List[Message], 
                            stream: bool = False,
                            **kwargs) -> LLMResponse:
        """Generate chat completion using OpenAI API"""
        
        # Format messages for OpenAI
        formatted_messages = self.format_messages(messages)
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            if stream:
                # Handle streaming
                response_content = ""
                stream_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=formatted_messages,
                    stream=True,
                    **params
                )
                
                async for chunk in stream_response:
                    if chunk.choices[0].delta.content:
                        response_content += chunk.choices[0].delta.content
                
                return LLMResponse(
                    content=response_content,
                    usage={"stream": True},
                    metadata={"provider": "openai", "model": self.model}
                )
            else:
                # Regular completion with tool calling
                available_tools = self._convert_mcp_tools_to_openai()
                
                # First API call with tools
                if available_tools:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=formatted_messages,
                        tools=available_tools,
                        **params
                    )
                else:
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=formatted_messages,
                        **params
                    )
                
                # Check if the model wants to call tools
                message = response.choices[0].message
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    # Execute tool calls
                    tool_results = []
                    for tool_call in message.tool_calls:
                        try:
                            args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                            result = await self.call_mcp_tool(tool_call.function.name, args)
                            tool_results.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "content": json.dumps(result)
                            })
                        except Exception as e:
                            tool_results.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool", 
                                "content": json.dumps({"error": str(e)})
                            })
                    
                    # Continue conversation with tool results
                    new_messages = formatted_messages + [
                        {
                            "role": "assistant",
                            "content": message.content,
                            "tool_calls": [{"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in message.tool_calls]
                        }
                    ] + tool_results
                    
                    # Second API call with tool results
                    final_response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=new_messages,
                        **params
                    )
                    
                    return LLMResponse(
                        content=final_response.choices[0].message.content,
                        usage={
                            "prompt_tokens": final_response.usage.prompt_tokens,
                            "completion_tokens": final_response.usage.completion_tokens,
                            "total_tokens": final_response.usage.total_tokens
                        } if final_response.usage else None,
                        metadata={
                            "provider": "openai",
                            "model": self.model,
                            "id": final_response.id,
                            "finish_reason": final_response.choices[0].finish_reason,
                            "tool_calls": len(message.tool_calls)
                        }
                    )
                else:
                    # No tool calls, return original response
                    return LLMResponse(
                        content=message.content,
                        usage={
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        } if response.usage else None,
                        metadata={
                            "provider": "openai",
                            "model": self.model,
                            "id": response.id,
                            "finish_reason": response.choices[0].finish_reason
                        }
                    )
                
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    async def chat_completion_stream(self, 
                                   messages: List[Message], 
                                   **kwargs) -> AsyncIterator[str]:
        """Generate streaming chat completion"""
        
        formatted_messages = self.format_messages(messages)
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            stream_response = await self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                stream=True,
                **params
            )
            
            async for chunk in stream_response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise Exception(f"OpenAI streaming error: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information"""
        model_info = {
            "provider": "openai",
            "model": self.model,
            "available_models": self.available_models,
            "supports_streaming": True,
            "supports_system_messages": True,
            "max_context_length": self._get_context_length(),
            "capabilities": [
                "text_generation",
                "conversation",
                "analysis",
                "code_generation",
                "function_calling"
            ]
        }
        return model_info
    
    def _get_context_length(self) -> int:
        """Get context length for different GPT models"""
        context_lengths = {
            "gpt-4.1": 1000000,      # 1M tokens for GPT-4.1
            "gpt-4.1-mini": 1000000, # 1M tokens for GPT-4.1-mini
            "gpt-4.1-nano": 128000,  # Estimated for nano
            "gpt-4o": 128000,        # GPT-4o context
            "gpt-4-turbo": 128000,   # Turbo context
            "gpt-4": 8192,           # Standard GPT-4
            "gpt-3.5-turbo": 16384   # Updated context
        }
        return context_lengths.get(self.model, 8192)
    
    def _convert_mcp_tools_to_openai(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to OpenAI function format"""
        if not self.mcp_client:
            return []
            
        tools = self.get_available_tools()
        openai_tools = []
        
        for tool in tools:
            function_def = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            openai_tools.append(function_def)
        
        return openai_tools
    
    async def test_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            test_messages = [Message(role="user", content="Hello")]
            response = await self.chat_completion(
                messages=test_messages,
                max_tokens=10
            )
            return response.content is not None
        except Exception:
            return False