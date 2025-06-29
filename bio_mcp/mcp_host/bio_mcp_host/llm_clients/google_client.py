import google.generativeai as genai
from typing import List, Dict, Any, AsyncIterator
from bio_mcp_host.llm_clients.base import BaseLLMClient, Message, LLMResponse, LLMConfig

class GoogleClient(BaseLLMClient):
    """Google Gemini client"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        genai.configure(api_key=self.api_key)
        
        # Latest models (2025)
        self.available_models = [
            "gemini-2.5-pro",        # Latest Gemini 2.5 Pro (2025)
            "gemini-2.0-flash-lite", # Lightweight version
            "gemini-1.5-pro",        # Previous flagship
            "gemini-1.5-flash",      # Fast model
            "gemini-1.0-pro"         # Legacy model
        ]
        
        # Initialize model
        self.gemini_model = genai.GenerativeModel(self.model)
    
    async def chat_completion(self, 
                            messages: List[Message], 
                            stream: bool = False,
                            **kwargs) -> LLMResponse:
        """Generate chat completion using Google Gemini API"""
        
        # Format messages for Gemini
        chat_history, current_message = self._format_messages_for_gemini(messages)
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        
        # Create generation config
        generation_config = self._create_generation_config(params)
        
        try:
            if stream:
                # Handle streaming
                response_content = ""
                chat = self.gemini_model.start_chat(history=chat_history)
                
                response_stream = await chat.send_message_async(
                    current_message,
                    generation_config=generation_config,
                    stream=True
                )
                
                async for chunk in response_stream:
                    if chunk.text:
                        response_content += chunk.text
                
                return LLMResponse(
                    content=response_content,
                    usage={"stream": True},
                    metadata={"provider": "google", "model": self.model}
                )
            else:
                # Regular completion
                if chat_history:
                    chat = self.gemini_model.start_chat(history=chat_history)
                    response = await chat.send_message_async(
                        current_message,
                        generation_config=generation_config
                    )
                else:
                    response = await self.gemini_model.generate_content_async(
                        current_message,
                        generation_config=generation_config
                    )
                
                return LLMResponse(
                    content=response.text,
                    usage={
                        "prompt_token_count": getattr(response.usage_metadata, 'prompt_token_count', None),
                        "candidates_token_count": getattr(response.usage_metadata, 'candidates_token_count', None),
                        "total_token_count": getattr(response.usage_metadata, 'total_token_count', None)
                    } if hasattr(response, 'usage_metadata') else None,
                    metadata={
                        "provider": "google",
                        "model": self.model,
                        "finish_reason": response.candidates[0].finish_reason.name if response.candidates else None
                    }
                )
                
        except Exception as e:
            raise Exception(f"Google Gemini API error: {str(e)}")
    
    async def chat_completion_stream(self, 
                                   messages: List[Message], 
                                   **kwargs) -> AsyncIterator[str]:
        """Generate streaming chat completion"""
        
        chat_history, current_message = self._format_messages_for_gemini(messages)
        
        # Prepare parameters
        params = self.get_default_params()
        params.update(kwargs)
        generation_config = self._create_generation_config(params)
        
        try:
            chat = self.gemini_model.start_chat(history=chat_history)
            response_stream = await chat.send_message_async(
                current_message,
                generation_config=generation_config,
                stream=True
            )
            
            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            raise Exception(f"Google Gemini streaming error: {str(e)}")
    
    def _format_messages_for_gemini(self, messages: List[Message]):
        """Format messages for Gemini API"""
        chat_history = []
        system_instructions = []
        
        # Separate system messages and regular conversation
        for msg in messages[:-1]:  # All but last message
            if msg.role == "system":
                system_instructions.append(msg.content)
            elif msg.role == "user":
                chat_history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                chat_history.append({"role": "model", "parts": [msg.content]})
        
        # Last message is the current prompt
        current_message = messages[-1].content if messages else ""
        
        # Prepend system instructions to current message if any
        if system_instructions:
            current_message = "\n".join(system_instructions) + "\n\n" + current_message
        
        return chat_history, current_message
    
    def _create_generation_config(self, params: Dict[str, Any]):
        """Create Gemini generation configuration"""
        config = {}
        
        if "max_tokens" in params:
            config["max_output_tokens"] = params["max_tokens"]
        if "temperature" in params:
            config["temperature"] = params["temperature"]
        if "top_p" in params:
            config["top_p"] = params["top_p"]
        if "top_k" in params:
            config["top_k"] = params["top_k"]
        
        return genai.GenerationConfig(**config) if config else None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Gemini model information"""
        model_info = {
            "provider": "google",
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
                "multimodal"
            ]
        }
        return model_info
    
    def _get_context_length(self) -> int:
        """Get context length for different Gemini models"""
        context_lengths = {
            "gemini-2.5-pro": 1000000,        # 1M tokens for Gemini 2.5 Pro
            "gemini-2.0-flash-lite": 1000000, # 1M tokens for lightweight
            "gemini-1.5-pro": 2000000,        # 2M tokens for 1.5 Pro
            "gemini-1.5-flash": 1000000,      # 1M tokens for Flash
            "gemini-1.0-pro": 32768           # Legacy context
        }
        return context_lengths.get(self.model, 32768)
    
    async def test_connection(self) -> bool:
        """Test Google Gemini API connection"""
        try:
            test_messages = [Message(role="user", content="Hello")]
            response = await self.chat_completion(
                messages=test_messages,
                max_tokens=1000
            )
            return response.content is not None
        except Exception:
            return False