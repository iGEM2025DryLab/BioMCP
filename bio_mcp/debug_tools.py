#!/usr/bin/env python3
"""Debug tool calling in BioMCP"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_host.bio_mcp_host.mcp_client.bio_mcp_client import BioMCPClient
from mcp_host.bio_mcp_host.llm_clients.google_client import GoogleClient
from mcp_host.bio_mcp_host.llm_clients.base import LLMConfig, LLMProvider, Message

async def debug_tool_calling():
    """Debug tool calling functionality"""
    
    # Load environment
    load_dotenv('.env')
    
    try:
        # 1. Create and connect MCP client
        print("🔧 Connecting to MCP server...")
        server_path = 'mcp_server/bio_mcp_server/main.py'
        mcp_client = BioMCPClient(['/usr/local/bin/python3', server_path])
        await mcp_client.connect()
        
        tools = mcp_client.get_available_tools()
        print(f"✅ Connected! Found {len(tools)} tools")
        
        # 2. Create Google client with MCP
        print("🤖 Creating Google client...")
        config = LLMConfig(
            provider=LLMProvider.GOOGLE,
            model=os.getenv('GOOGLE_MODEL', 'gemini-1.5-flash'),
            api_key=os.getenv('GOOGLE_API_KEY')
        )
        google_client = GoogleClient(config, mcp_client)
        
        # 3. Check tool conversion
        gemini_tools = google_client._convert_mcp_tools_to_gemini()
        print(f"🔄 Converted {len(gemini_tools)} tools for Gemini")
        
        if gemini_tools:
            print("📋 Available tools:")
            for tool in gemini_tools[:5]:  # Show first 5
                print(f"  - {tool['name']}: {tool['description'][:60]}...")
        
        # 4. Test a simple chat that should trigger tool calling
        print("\n💬 Testing tool calling...")
        test_message = Message(role="user", content="List the files I have uploaded")
        
        response = await google_client.chat_completion([test_message])
        print(f"📤 Response: {response.content}")
        
        if 'function_calls' in response.metadata and response.metadata['function_calls']:
            print(f"✅ Function calls detected: {response.metadata['function_calls']}")
        else:
            print("❌ No function calls detected")
        
        await mcp_client.disconnect()
        print("🔌 Disconnected")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_tool_calling())