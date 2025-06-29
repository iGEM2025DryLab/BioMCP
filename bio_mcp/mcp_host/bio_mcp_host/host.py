import asyncio
import json
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from bio_mcp_host.llm_manager import LLMManager
from bio_mcp_host.llm_clients.base import Message, LLMResponse
from bio_mcp_host.mcp_client.bio_mcp_client import BioMCPClient

@dataclass
class ChatSession:
    """Represents a chat session"""
    session_id: str
    messages: List[Message]
    created_at: datetime
    llm_client: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BioMCPHost:
    """Main host that coordinates LLMs and MCP server communication"""
    
    def __init__(self, bio_mcp_server_command: List[str]):
        self.llm_manager = LLMManager()
        self.bio_mcp_client = BioMCPClient(bio_mcp_server_command)
        self.chat_sessions: Dict[str, ChatSession] = {}
        self.connected = False
    
    async def start(self):
        """Start the host and connect to Bio MCP Server"""
        print("🚀 Starting Bio MCP Host...")
        
        # Connect to Bio MCP Server
        print("📡 Connecting to Bio MCP Server...")
        success = await self.bio_mcp_client.connect()
        if not success:
            raise RuntimeError("Failed to connect to Bio MCP Server")
        
        self.connected = True
        print("✅ Connected to Bio MCP Server")
        
        # Test LLM connections
        print("🧠 Testing LLM connections...")
        connection_results = await self.llm_manager.test_all_connections()
        
        for client_name, status in connection_results.items():
            status_text = "✅" if status else "❌"
            print(f"  {status_text} {client_name}")
        
        if not any(connection_results.values()):
            print("⚠️  Warning: No LLM clients are available (check your API keys)")
        
        print("🎉 Bio MCP Host started successfully!")
        print(f"🔧 Available tools: {len(self.bio_mcp_client.get_available_tools())}")
        print(f"🤖 Available LLM clients: {', '.join(self.llm_manager.list_clients())}")
        print("📝 Ready for interactive commands!")
    
    async def stop(self):
        """Stop the host and disconnect from services"""
        print("Stopping Bio MCP Host...")
        await self.bio_mcp_client.disconnect()
        self.connected = False
        print("Bio MCP Host stopped.")
    
    def create_chat_session(self, session_id: str, llm_client: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            session_id=session_id,
            messages=[],
            created_at=datetime.now(),
            llm_client=llm_client,
            metadata={}
        )
        self.chat_sessions[session_id] = session
        return session
    
    def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Get an existing chat session"""
        return self.chat_sessions.get(session_id)
    
    def delete_chat_session(self, session_id: str):
        """Delete a chat session"""
        if session_id in self.chat_sessions:
            del self.chat_sessions[session_id]
    
    async def chat(self, 
                  session_id: str, 
                  user_message: str,
                  llm_client: Optional[str] = None,
                  system_message: Optional[str] = None,
                  stream: bool = False) -> LLMResponse:
        """Chat with LLM, with access to bio tools"""
        
        if not self.connected:
            raise RuntimeError("Host not connected to Bio MCP Server")
        
        # Get or create session
        session = self.get_chat_session(session_id)
        if not session:
            session = self.create_chat_session(session_id, llm_client)
        
        # Add system message if this is the first message
        if not session.messages and system_message:
            session.messages.append(Message(role="system", content=system_message))
        elif not session.messages:
            # Default system message for bio research
            default_system = self._get_default_system_message()
            session.messages.append(Message(role="system", content=default_system))
        
        # Add user message
        session.messages.append(Message(role="user", content=user_message))
        
        # Determine which LLM client to use
        client_name = llm_client or session.llm_client
        
        try:
            # Get LLM response
            response = await self.llm_manager.chat_completion(
                messages=session.messages,
                client_name=client_name,
                stream=stream
            )
            
            # Add assistant response to session
            session.messages.append(Message(role="assistant", content=response.content))
            
            return response
            
        except Exception as e:
            # Add error message to session
            error_msg = f"Error: {str(e)}"
            session.messages.append(Message(role="assistant", content=error_msg))
            raise
    
    async def chat_stream(self,
                         session_id: str,
                         user_message: str,
                         llm_client: Optional[str] = None,
                         system_message: Optional[str] = None) -> AsyncIterator[str]:
        """Stream chat response"""
        
        if not self.connected:
            raise RuntimeError("Host not connected to Bio MCP Server")
        
        # Get or create session
        session = self.get_chat_session(session_id)
        if not session:
            session = self.create_chat_session(session_id, llm_client)
        
        # Add system message if needed
        if not session.messages and system_message:
            session.messages.append(Message(role="system", content=system_message))
        elif not session.messages:
            default_system = self._get_default_system_message()
            session.messages.append(Message(role="system", content=default_system))
        
        # Add user message
        session.messages.append(Message(role="user", content=user_message))
        
        # Determine LLM client
        client_name = llm_client or session.llm_client
        
        # Stream response
        full_response = ""
        try:
            async for chunk in self.llm_manager.chat_completion_stream(
                messages=session.messages,
                client_name=client_name
            ):
                full_response += chunk
                yield chunk
            
            # Add complete response to session
            session.messages.append(Message(role="assistant", content=full_response))
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            session.messages.append(Message(role="assistant", content=error_msg))
            yield error_msg
    
    def _get_default_system_message(self) -> str:
        """Get default system message for bio research"""
        available_tools = self.bio_mcp_client.get_available_tools()
        tool_descriptions = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in available_tools
        ])
        
        return f"""You are a helpful AI assistant specialized in biological research. You have access to bio-analysis tools through an MCP server.

Available tools:
{tool_descriptions}

You can help with:
- Protein structure analysis and visualization
- pKa calculations using PROPKA
- DNA/RNA sequence analysis
- File management for biological data
- Structural biology research

When users ask about biological analysis, use the appropriate tools to help them. Always explain what you're doing and provide clear interpretations of results."""
    
    # Bio tool access methods
    
    async def upload_file(self, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Upload file to bio server"""
        return await self.bio_mcp_client.upload_file(file_path, filename)
    
    async def list_files(self, bio_type: Optional[str] = None) -> Dict[str, Any]:
        """List files on bio server"""
        return await self.bio_mcp_client.list_files(bio_type)
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get file information"""
        return await self.bio_mcp_client.get_file_info(file_id)
    
    async def calculate_pka(self, file_id: str, ph: float = 7.0) -> Dict[str, Any]:
        """Calculate pKa values"""
        return await self.bio_mcp_client.calculate_pka(file_id, ph)
    
    async def visualize_structure(self, file_id: str, style: str = "cartoon") -> Dict[str, Any]:
        """Create structure visualization"""
        return await self.bio_mcp_client.visualize_structure(file_id, style)
    
    # Status and info methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get host status"""
        return {
            "connected": self.connected,
            "llm_clients": self.llm_manager.get_all_clients_info(),
            "active_sessions": len(self.chat_sessions),
            "available_tools": len(self.bio_mcp_client.get_available_tools()) if self.connected else 0
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get available bio tools"""
        if not self.connected:
            return []
        return self.bio_mcp_client.get_available_tools()
    
    def get_llm_clients(self) -> Dict[str, Dict[str, Any]]:
        """Get LLM client information"""
        return self.llm_manager.get_all_clients_info()
    
    def switch_llm_model(self, client_name: str, new_model: str):
        """Switch model for an LLM client"""
        return self.llm_manager.switch_model(client_name, new_model)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            "host_status": "healthy" if self.connected else "disconnected",
            "bio_server_connection": await self.bio_mcp_client.health_check() if self.connected else False,
            "llm_connections": await self.llm_manager.test_all_connections(),
            "timestamp": datetime.now().isoformat()
        }