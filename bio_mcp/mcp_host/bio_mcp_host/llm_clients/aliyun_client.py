import dashscope
from typing import List, Dict, Any, AsyncIterator
from bio_mcp_host.llm_clients.base import BaseLLMClient, Message, LLMResponse, LLMConfig

class AliyunClient(BaseLLMClient):
    """Aliyun Qwen client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        dashscope.api_key = self.api_key
        
        # Latest models (2025)
        self.available_models = [
            "qwen-2.5-vl",      # Latest Qwen 2.5 VL (2025)
            "qwen-2.5",         # Qwen 2.5 standard
            "qwen-2",           # Qwen 2 series
            "qwen-max",         # Maximum capability
            "qwen-plus",        # Balanced model
            "qwen-turbo"        # Fast model
        ]
    
    async def chat_completion(self, 
                            messages: List[Message], 
                            stream: bool = False,
                            **kwargs) -> LLMResponse:
        """Generate chat completion using Aliyun Qwen API"""
        
        # Format messages for Qwen
        formatted_messages = self.format_messages(messages)
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        params = {k: v for k, v in params.items() if v is not None}
        
        try:
            if stream:
                # Handle streaming
                response_content = ""
                responses = dashscope.Generation.call(
                    model=self.model,
                    messages=formatted_messages,
                    stream=True,
                    **params
                )
                
                for response in responses:
                    if response.status_code == 200:
                        if response.output and response.output.choices:
                            delta = response.output.choices[0].message.content
                            if delta:
                                response_content += delta
                
                return LLMResponse(
                    content=response_content,
                    usage={"stream": True},
                    metadata={"provider": "aliyun", "model": self.model}
                )
            else:
                # Regular completion
                response = dashscope.Generation.call(
                    model=self.model,
                    messages=formatted_messages,
                    **params
                )
                
                if response.status_code != 200:
                    raise Exception(f"Aliyun API error: {response.message}")
                
                return LLMResponse(
                    content=response.output.choices[0].message.content,
                    usage={
                        "input_tokens": response.usage.input_tokens if response.usage else None,
                        "output_tokens": response.usage.output_tokens if response.usage else None,
                        "total_tokens": response.usage.total_tokens if response.usage else None
                    },
                    metadata={
                        "provider": "aliyun",
                        "model": self.model,
                        "request_id": response.request_id,
                        "finish_reason": response.output.choices[0].finish_reason if response.output.choices else None
                    }
                )
                
        except Exception as e:
            raise Exception(f"Aliyun Qwen API error: {str(e)}")
    
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
            responses = dashscope.Generation.call(
                model=self.model,
                messages=formatted_messages,
                stream=True,
                **params
            )
            
            for response in responses:
                if response.status_code == 200:
                    if response.output and response.output.choices:
                        delta = response.output.choices[0].message.content
                        if delta:
                            yield delta
                            
        except Exception as e:
            raise Exception(f"Aliyun Qwen streaming error: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Qwen model information"""
        model_info = {
            "provider": "aliyun",
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
                "chinese_language"
            ]
        }
        return model_info
    
    def _get_context_length(self) -> int:
        """Get context length for different Qwen models"""
        context_lengths = {
            "qwen-2.5-vl": 32000,   # Latest VL model
            "qwen-2.5": 32000,      # Qwen 2.5 context
            "qwen-2": 32000,        # Qwen 2 context
            "qwen-max": 30000,      # Maximum model
            "qwen-plus": 30000,     # Plus model
            "qwen-turbo": 8000      # Turbo model
        }
        return context_lengths.get(self.model, 8000)
    
    async def test_connection(self) -> bool:
        """Test Aliyun Qwen API connection"""
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
        """Get default parameters for Aliyun Qwen"""
        params = super().get_default_params()
        
        # Map parameter names for Qwen API
        if "max_tokens" in params:
            params["max_output_tokens"] = params.pop("max_tokens")
            
        return params