import anthropic
from typing import List, Dict, Any, AsyncIterator
from bio_mcp_host.llm_clients.base import BaseLLMClient, Message, LLMResponse, LLMConfig

class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
        
        # Latest models (2025)
        self.available_models = [
            "claude-3-7-sonnet-20250210",  # Latest Claude 3.7 Sonnet (2025)
            "claude-3-5-sonnet-20241022",  # Previous flagship
            "claude-3-5-haiku-20241022",   # Lightweight model 
            "claude-3-opus-20240229",      # Most capable previous model
            "claude-3-sonnet-20240229",    # Balanced model
            "claude-3-haiku-20240307"      # Fast model
        ]
    
    async def chat_completion(self, 
                            messages: List[Message], 
                            stream: bool = False,
                            **kwargs) -> LLMResponse:
        """Generate chat completion using Anthropic API"""
        
        # Format messages for Anthropic
        formatted_messages = []
        system_message = None
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            if stream:
                # Handle streaming
                response_content = ""
                async with self.client.messages.stream(
                    model=self.model,
                    messages=formatted_messages,
                    system=system_message,
                    **params
                ) as stream:
                    async for text in stream.text_stream:
                        response_content += text
                
                return LLMResponse(
                    content=response_content,
                    usage={"stream": True},
                    metadata={"provider": "anthropic", "model": self.model}
                )
            else:
                # Regular completion
                response = await self.client.messages.create(
                    model=self.model,
                    messages=formatted_messages,
                    system=system_message,
                    **params
                )
                
                return LLMResponse(
                    content=response.content[0].text,
                    usage={
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                    },
                    metadata={
                        "provider": "anthropic",
                        "model": self.model,
                        "id": response.id
                    }
                )
                
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    async def chat_completion_stream(self, 
                                   messages: List[Message], 
                                   **kwargs) -> AsyncIterator[str]:
        """Generate streaming chat completion"""
        
        # Format messages for Anthropic
        formatted_messages = []
        system_message = None
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            async with self.client.messages.stream(
                model=self.model,
                messages=formatted_messages,
                system=system_message,
                **params
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            raise Exception(f"Anthropic streaming error: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Claude model information"""
        model_info = {
            "provider": "anthropic",
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
                "tool_use"
            ]
        }
        return model_info
    
    def _get_context_length(self) -> int:
        """Get context length for different Claude models"""
        context_lengths = {
            "claude-3-7-sonnet-20250210": 200000,  # Latest model
            "claude-3-5-sonnet-20241022": 200000,
            "claude-3-5-haiku-20241022": 200000,
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000
        }
        return context_lengths.get(self.model, 200000)
    
    async def test_connection(self) -> bool:
        """Test Anthropic API connection"""
        try:
            test_messages = [Message(role="user", content="Hello")]
            response = await self.chat_completion(
                messages=test_messages,
                max_tokens=10
            )
            return response.content is not None
        except Exception:
            return False
    
    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for Anthropic"""
        params = super().get_default_params()
        
        # Set default max_tokens if not specified
        if "max_tokens" not in params:
            params["max_tokens"] = 4000
            
        return params