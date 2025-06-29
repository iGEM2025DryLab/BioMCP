import openai
from typing import List, Dict, Any, AsyncIterator
from bio_mcp_host.llm_clients.base import BaseLLMClient, Message, LLMResponse, LLMConfig

class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
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
                # Regular completion
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=formatted_messages,
                    **params
                )
                
                return LLMResponse(
                    content=response.choices[0].message.content,
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