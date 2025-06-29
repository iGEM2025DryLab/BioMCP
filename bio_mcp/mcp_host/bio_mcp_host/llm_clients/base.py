from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass
from enum import Enum

class LLMProvider(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    ALIYUN = "aliyun"

@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LLMResponse:
    content: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class LLMConfig:
    provider: LLMProvider
    model: str
    api_key: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    additional_params: Optional[Dict[str, Any]] = None

class BaseLLMClient(ABC):
    """Base class for all LLM clients"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self.api_key = config.api_key
        
    @abstractmethod
    async def chat_completion(self, 
                            messages: List[Message], 
                            stream: bool = False,
                            **kwargs) -> LLMResponse:
        """
        Generate chat completion
        
        Args:
            messages: List of conversation messages
            stream: Whether to stream the response
            **kwargs: Additional model-specific parameters
            
        Returns:
            LLMResponse object
        """
        pass
    
    @abstractmethod
    async def chat_completion_stream(self, 
                                   messages: List[Message], 
                                   **kwargs) -> AsyncIterator[str]:
        """
        Generate streaming chat completion
        
        Args:
            messages: List of conversation messages
            **kwargs: Additional model-specific parameters
            
        Yields:
            Partial response strings
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the client can connect to the API"""
        pass
    
    def format_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert Message objects to API format"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def get_default_params(self) -> Dict[str, Any]:
        """Get default parameters for this client"""
        params = {}
        if self.config.max_tokens:
            params["max_tokens"] = self.config.max_tokens
        if self.config.temperature is not None:
            params["temperature"] = self.config.temperature
        if self.config.additional_params:
            params.update(self.config.additional_params)
        return params