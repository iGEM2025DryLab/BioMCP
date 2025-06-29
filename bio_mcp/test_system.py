#!/usr/bin/env python3
"""
Simple system test for Bio MCP
"""

import asyncio
import sys
import os

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mcp_host'))

async def test_system():
    """Test Bio MCP system components"""
    print("🧪 Testing Bio MCP System...")
    
    try:
        # Test MCP client
        from bio_mcp_host.mcp_client.bio_mcp_client import BioMCPClient
        
        client = BioMCPClient(["python3", "run_server.py"])
        
        print("📡 Testing MCP connection...")
        success = await client.connect()
        
        if success:
            print("✅ MCP connection successful!")
            
            tools = client.get_available_tools()
            print(f"🔧 Found {len(tools)} tools")
            
            health = await client.health_check()
            print(f"🏥 Health check: {'✅ Healthy' if health else '❌ Unhealthy'}")
            
            await client.disconnect()
            print("🔌 Disconnected")
            
            print("\n🎉 Bio MCP System Test PASSED!")
            print("✅ Ready to use! Run: python3 bio_mcp.py interactive")
            return True
            
        else:
            print("❌ MCP connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def main():
    """Run the test"""
    success = await test_system()
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(1)