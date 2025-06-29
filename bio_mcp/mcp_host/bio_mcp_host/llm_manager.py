from typing import Dict, List, Optional, Any, AsyncIterator
import os
from bio_mcp_host.llm_clients.base import BaseLLMClient, LLMProvider, LLMConfig, Message, LLMResponse
from bio_mcp_host.llm_clients.anthropic_client import AnthropicClient
from bio_mcp_host.llm_clients.openai_client import OpenAIClient
from bio_mcp_host.llm_clients.google_client import GoogleClient
from bio_mcp_host.llm_clients.aliyun_client import AliyunClient

class LLMManager:
    """Manages multiple LLM clients and provides unified interface"""
    
    def __init__(self):
        self.clients: Dict[str, BaseLLMClient] = {}
        self.default_client: Optional[str] = None
        self._load_clients_from_env()
    
    def _load_clients_from_env(self):
        """Load LLM clients from environment variables"""
        
        # Anthropic Claude
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                config = LLMConfig(
                    provider=LLMProvider.ANTHROPIC,
                    model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                    api_key=anthropic_key,
                    max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "4000")),
                    temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7"))
                )
                self.add_client("anthropic", AnthropicClient(config))
                if not self.default_client:
                    self.default_client = "anthropic"
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")
        
        # OpenAI GPT
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                config = LLMConfig(
                    provider=LLMProvider.OPENAI,
                    model=os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
                    api_key=openai_key,
                    max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
                    temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
                )
                self.add_client("openai", OpenAIClient(config))
                if not self.default_client:
                    self.default_client = "openai"
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
        
        # Google Gemini
        google_key = os.getenv("GOOGLE_API_KEY")
        if google_key:
            try:
                config = LLMConfig(
                    provider=LLMProvider.GOOGLE,
                    model=os.getenv("GOOGLE_MODEL", "gemini-1.5-pro"),
                    api_key=google_key,
                    max_tokens=int(os.getenv("GOOGLE_MAX_TOKENS", "4000")),
                    temperature=float(os.getenv("GOOGLE_TEMPERATURE", "0.7"))
                )
                self.add_client("google", GoogleClient(config))
                if not self.default_client:
                    self.default_client = "google"
            except Exception as e:
                print(f"Failed to initialize Google client: {e}")
        
        # Aliyun Qwen
        aliyun_key = os.getenv("DASHSCOPE_API_KEY")
        if aliyun_key:
            try:
                config = LLMConfig(
                    provider=LLMProvider.ALIYUN,
                    model=os.getenv("ALIYUN_MODEL", "qwen-max"),
                    api_key=aliyun_key,
                    max_tokens=int(os.getenv("ALIYUN_MAX_TOKENS", "4000")),
                    temperature=float(os.getenv("ALIYUN_TEMPERATURE", "0.7"))
                )
                self.add_client("aliyun", AliyunClient(config))
                if not self.default_client:
                    self.default_client = "aliyun"
            except Exception as e:
                print(f"Failed to initialize Aliyun client: {e}")
    
    def add_client(self, name: str, client: BaseLLMClient):
        """Add an LLM client"""
        self.clients[name] = client
    
    def remove_client(self, name: str):
        """Remove an LLM client"""
        if name in self.clients:
            del self.clients[name]
            if self.default_client == name:
                self.default_client = next(iter(self.clients.keys())) if self.clients else None
    
    def set_default_client(self, name: str):
        """Set the default client"""
        if name in self.clients:
            self.default_client = name
        else:
            raise ValueError(f"Client '{name}' not found")
    
    def get_client(self, name: Optional[str] = None) -> BaseLLMClient:
        """Get a specific client or the default client"""
        client_name = name or self.default_client
        if not client_name:
            raise ValueError("No client specified and no default client set")
        if client_name not in self.clients:
            raise ValueError(f"Client '{client_name}' not found")
        return self.clients[client_name]
    
    def list_clients(self) -> List[str]:
        """List all available clients"""
        return list(self.clients.keys())
    
    def get_client_info(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a client"""
        client = self.get_client(name)
        info = client.get_model_info()
        info["is_default"] = (name or self.default_client) == self.default_client
        return info
    
    def get_all_clients_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all clients"""
        return {name: self.get_client_info(name) for name in self.clients.keys()}
    
    async def chat_completion(self, 
                            messages: List[Message],
                            client_name: Optional[str] = None,
                            stream: bool = False,
                            **kwargs) -> LLMResponse:
        """Generate chat completion using specified or default client"""
        client = self.get_client(client_name)
        return await client.chat_completion(messages, stream=stream, **kwargs)
    
    async def chat_completion_stream(self, 
                                   messages: List[Message],
                                   client_name: Optional[str] = None,
                                   **kwargs) -> AsyncIterator[str]:
        """Generate streaming chat completion using specified or default client"""
        client = self.get_client(client_name)
        async for chunk in client.chat_completion_stream(messages, **kwargs):
            yield chunk
    
    async def test_all_connections(self) -> Dict[str, bool]:
        """Test connections for all clients"""
        results = {}
        for name, client in self.clients.items():
            try:
                results[name] = await client.test_connection()
            except Exception:
                results[name] = False
        return results
    
    async def test_connection(self, client_name: Optional[str] = None) -> bool:
        """Test connection for a specific client"""
        client = self.get_client(client_name)
        return await client.test_connection()
    
    def create_client_from_config(self, name: str, config: LLMConfig) -> BaseLLMClient:
        """Create and add a client from configuration"""
        if config.provider == LLMProvider.ANTHROPIC:
            client = AnthropicClient(config)
        elif config.provider == LLMProvider.OPENAI:
            client = OpenAIClient(config)
        elif config.provider == LLMProvider.GOOGLE:
            client = GoogleClient(config)
        elif config.provider == LLMProvider.ALIYUN:
            client = AliyunClient(config)
        else:
            raise ValueError(f"Unsupported provider: {config.provider}")
        
        self.add_client(name, client)
        return client
    
    def get_available_models(self, client_name: Optional[str] = None) -> List[str]:
        """Get available models for a client"""
        client = self.get_client(client_name)
        return client.get_model_info()["available_models"]
    
    def switch_model(self, client_name: str, new_model: str):
        """Switch model for a specific client"""
        if client_name not in self.clients:
            raise ValueError(f"Client '{client_name}' not found")
        
        old_client = self.clients[client_name]
        old_config = old_client.config
        
        # Create new config with different model
        new_config = LLMConfig(
            provider=old_config.provider,
            model=new_model,
            api_key=old_config.api_key,
            max_tokens=old_config.max_tokens,
            temperature=old_config.temperature,
            additional_params=old_config.additional_params
        )
        
        # Replace client
        new_client = self.create_client_from_config(client_name, new_config)
        return new_client