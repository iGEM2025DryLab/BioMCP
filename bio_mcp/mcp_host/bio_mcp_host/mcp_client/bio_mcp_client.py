#!/usr/bin/env python3
"""
Bio MCP Client - Latest MCP SDK implementation with proper stdio transport
"""

import asyncio
import json
import base64
import os
from typing import Dict, List, Any, Optional, AsyncIterator
from pathlib import Path
from contextlib import AsyncExitStack

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

class BioMCPClient:
    """Bio MCP Client using latest MCP SDK patterns with fallback to direct JSON-RPC"""
    
    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.available_tools: List[Dict[str, Any]] = []
        self.connected = False
        
        # SDK-based components
        self.session: Optional[ClientSession] = None
        self.exit_stack: Optional[AsyncExitStack] = None
        
        # Fallback direct connection components
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id = 1
        self.use_sdk = SDK_AVAILABLE
    
    def _get_next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def connect(self) -> bool:
        """Connect to the Bio MCP Server using latest SDK patterns"""
        try:
            if self.use_sdk:
                return await self._connect_with_sdk()
            else:
                return await self._connect_direct()
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
            await self.disconnect()
            return False
    
    async def _connect_with_sdk(self) -> bool:
        """Connect using the official MCP SDK"""
        print("   🔧 Starting MCP server with SDK...")
        
        # Determine command and args from server_command
        if len(self.server_command) == 1:
            # Single script file
            script_path = self.server_command[0]
            if script_path.endswith('.py'):
                command = "python"
                args = [script_path]
            elif script_path.endswith('.js'):
                command = "node" 
                args = [script_path]
            else:
                raise ValueError("Server script must be a .py or .js file")
        else:
            # Command with args
            command = self.server_command[0]
            args = self.server_command[1:]
        
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Create server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )
        
        print("   📋 Initializing MCP session with SDK...")
        
        # Initialize connection using SDK
        self.exit_stack = AsyncExitStack()
        
        # Establish stdio transport
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        
        # Create and initialize session
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        
        await self.session.initialize()
        print("   ✅ Session initialized successfully!")
        
        # Get available tools
        print("   🔍 Loading available tools...")
        tools_response = await self.session.list_tools()
        
        if tools_response and hasattr(tools_response, 'tools'):
            self.available_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema
                }
                for tool in tools_response.tools
            ]
            print(f"   📋 Found {len(self.available_tools)} tools")
        
        self.connected = True
        return True
    
    async def _connect_direct(self) -> bool:
        """Connect using direct JSON-RPC (fallback method)"""
        print("   🔧 Starting MCP server process (direct mode)...")
        
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        # Start server process
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        print("   📋 Initializing MCP session...")
        
        # Send initialize message
        init_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "bio-mcp-host", "version": "1.0.0"}
            }
        }
        
        response = await self._send_request(init_request)
        if not response or 'error' in response:
            raise Exception(f"Initialization failed: {response.get('error', 'Unknown error')}")
        
        print("   ✅ Session initialized successfully!")
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await self._send_notification(initialized_notification)
        
        # Get available tools
        print("   🔍 Loading available tools...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/list"
        }
        
        tools_response = await self._send_request(tools_request)
        if tools_response and 'result' in tools_response:
            self.available_tools = tools_response['result'].get('tools', [])
            print(f"   📋 Found {len(self.available_tools)} tools")
        
        self.connected = True
        return True
    
    async def _send_request(self, request: Dict[str, Any], timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request and wait for response"""
        if not self.process:
            raise RuntimeError("Not connected to server")
        
        try:
            # Send request
            message = json.dumps(request) + "\n"
            self.process.stdin.write(message.encode())
            await self.process.stdin.drain()
            
            # Read response with timeout
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), timeout=timeout
            )
            
            if not response_line:
                return None
            
            response = json.loads(response_line.decode().strip())
            return response
            
        except asyncio.TimeoutError:
            raise Exception(f"Request timed out after {timeout} seconds")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")
        except Exception as e:
            raise Exception(f"Request failed: {e}")
    
    async def _send_notification(self, notification: Dict[str, Any]):
        """Send a JSON-RPC notification (no response expected)"""
        if not self.process:
            raise RuntimeError("Not connected to server")
        
        message = json.dumps(notification) + "\n"
        self.process.stdin.write(message.encode())
        await self.process.stdin.drain()
    
    async def disconnect(self):
        """Disconnect from the Bio MCP Server"""
        self.connected = False
        
        # Clean up SDK connection
        if self.exit_stack:
            try:
                await self.exit_stack.aclose()
            except:
                pass
            self.exit_stack = None
        
        self.session = None
        
        # Clean up direct connection
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except:
                pass
            self.process = None
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return [
            {
                "name": tool.get("name"),
                "description": tool.get("description"),
                "parameters": tool.get("inputSchema", {})
            }
            for tool in self.available_tools
        ]
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the Bio MCP Server"""
        if not self.connected:
            raise RuntimeError("Not connected to Bio MCP Server")
        
        try:
            if self.use_sdk and self.session:
                return await self._call_tool_sdk(tool_name, arguments)
            else:
                return await self._call_tool_direct(tool_name, arguments)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "arguments": arguments
            }
    
    async def _call_tool_sdk(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool using MCP SDK"""
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # Extract text content from MCP response format
            content_text = ""
            if hasattr(result, 'content') and result.content:
                for content_item in result.content:
                    if hasattr(content_item, 'type') and content_item.type == 'text':
                        content_text += getattr(content_item, 'text', '')
            
            return {
                "success": True,
                "result": content_text or str(result),
                "tool": tool_name,
                "arguments": arguments,
                "raw_result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "arguments": arguments
            }
    
    async def _call_tool_direct(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool using direct JSON-RPC"""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(request)
        
        if not response:
            return {
                "success": False,
                "error": "No response from server",
                "tool": tool_name,
                "arguments": arguments
            }
        
        if 'error' in response:
            return {
                "success": False,
                "error": response['error'].get('message', str(response['error'])),
                "tool": tool_name,
                "arguments": arguments
            }
        
        if 'result' in response:
            result = response['result']
            
            # Extract text content from MCP response format
            content_text = ""
            if 'content' in result:
                for content_item in result['content']:
                    if content_item.get('type') == 'text':
                        content_text += content_item.get('text', '')
            
            return {
                "success": True,
                "result": content_text or str(result),
                "tool": tool_name,
                "arguments": arguments,
                "raw_result": result
            }
        
        return {
            "success": False,
            "error": "Unexpected response format",
            "tool": tool_name,
            "arguments": arguments,
            "raw_response": response
        }
    
    # Convenience methods for common operations
    
    async def upload_file(self, file_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to the bio file system"""
        file_path = Path(file_path)
        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        # Read and encode file
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
        
        filename = filename or file_path.name
        
        return await self.call_tool("upload_file", {
            "filename": filename,
            "content": content
        })
    
    async def list_files(self, bio_type: Optional[str] = None) -> Dict[str, Any]:
        """List files in the bio file system"""
        args = {}
        if bio_type:
            args["bio_type"] = bio_type
        
        return await self.call_tool("list_files", args)
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Get information about a specific file"""
        return await self.call_tool("get_file_info", {"file_id": file_id})
    
    async def read_file_content(self, file_id: str, start_line: int = 0, max_lines: int = 1000) -> Dict[str, Any]:
        """Read file content with line range"""
        return await self.call_tool("read_file_content", {
            "file_id": file_id,
            "start_line": start_line,
            "max_lines": max_lines
        })
    
    async def calculate_pka(self, file_id: str, ph: float = 7.0, chains: Optional[List[str]] = None, residue_range: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
        """Calculate pKa values using PROPKA"""
        args = {
            "file_id": file_id,
            "ph": ph
        }
        if chains:
            args["chains"] = chains
        if residue_range:
            args["residue_range"] = residue_range
        
        return await self.call_tool("calculate_pka", args)
    
    async def visualize_structure(self, file_id: str, style: str = "cartoon", chains: Optional[List[str]] = None, residues: Optional[List[str]] = None, width: int = 800, height: int = 600) -> Dict[str, Any]:
        """Create structure visualization using PyMOL"""
        args = {
            "file_id": file_id,
            "style": style,
            "width": width,
            "height": height
        }
        if chains:
            args["chains"] = chains
        if residues:
            args["residues"] = residues
        
        return await self.call_tool("visualize_structure", args)
    
    async def health_check(self) -> bool:
        """Check if connection to server is healthy"""
        try:
            if not self.connected:
                return False
            
            # Try to list files as a simple health check
            result = await self.list_files()
            return result.get("success", False)
        except Exception:
            return False