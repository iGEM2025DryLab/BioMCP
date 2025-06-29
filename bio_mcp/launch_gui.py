#!/usr/bin/env python3
"""
Quick GUI launcher for Bio MCP system
"""

import asyncio
import sys
import os
from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import json

# Add to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mcp_host'))

app = FastAPI(title="Bio MCP GUI", description="Web interface for Bio MCP system")

# Simple HTML interface
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Bio MCP System</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
        .status.success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .status.warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
        .status.error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        .button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .button:hover { background: #0056b3; }
        .button.secondary { background: #6c757d; }
        .button.success { background: #28a745; }
        #chat-area { height: 300px; border: 1px solid #ddd; padding: 10px; overflow-y: scroll; background: #f8f9fa; margin: 10px 0; }
        #chat-input { width: 70%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .command-list { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .command { font-family: monospace; background: white; padding: 5px 10px; margin: 5px 0; border-radius: 3px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧬 Bio MCP System</h1>
            <p>AI-powered biological research platform</p>
        </div>
        
        <div class="status warning">
            <strong>⚠️ Note:</strong> The MCP server connection has known timeout issues. 
            The system works best in interactive command-line mode for now.
        </div>
        
        <div class="section">
            <h2>🚀 Quick Start</h2>
            <p>To use the full Bio MCP system, run these commands in your terminal:</p>
            
            <div class="command-list">
                <div class="command">cd /Users/zhaoj/Project/BioMCP/BioMCP/bio_mcp</div>
                <div class="command">python3 run_host.py --interactive</div>
            </div>
            
            <p>Even if the server connection fails, you can still use many features!</p>
        </div>
        
        <div class="section">
            <h2>🎯 Available Commands</h2>
            <div class="command-list">
                <div class="command">status - Show system status</div>
                <div class="command">clients - List LLM clients</div>
                <div class="command">health - Health check</div>
                <div class="command">chat &lt;message&gt; - Chat with AI (requires API keys)</div>
                <div class="command">upload &lt;file&gt; - Upload bio file (requires server)</div>
                <div class="command">files - List uploaded files (requires server)</div>
                <div class="command">tools - List available tools (requires server)</div>
                <div class="command">quit - Exit</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🔧 Features</h2>
            <ul>
                <li><strong>Multi-LLM Support:</strong> Anthropic, OpenAI, Google, Aliyun</li>
                <li><strong>Bio Analysis Tools:</strong> PROPKA, PyMOL integration</li>
                <li><strong>Smart File System:</strong> Context-efficient reading for large bio files</li>
                <li><strong>Structure Analysis:</strong> Protein structure visualization and analysis</li>
                <li><strong>pKa Calculations:</strong> PROPKA-powered ionization analysis</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>📝 API Configuration</h2>
            <p>To enable LLM features, create a <code>.env</code> file with your API keys:</p>
            <div class="command-list">
                <div class="command">ANTHROPIC_API_KEY=your_key_here</div>
                <div class="command">OPENAI_API_KEY=your_key_here</div>
                <div class="command">GOOGLE_API_KEY=your_key_here</div>
                <div class="command">DASHSCOPE_API_KEY=your_key_here</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🔬 Test Results</h2>
            <div class="status success">✅ File System - Working</div>
            <div class="status success">✅ Bio Tools (PROPKA, PyMOL) - Working</div>
            <div class="status success">✅ Host System - Working</div>
            <div class="status success">✅ GUI Components - Working</div>
            <div class="status error">❌ MCP Server Connection - Timeout Issues</div>
        </div>
        
        <div class="section">
            <h2>🛠️ Troubleshooting</h2>
            <ol>
                <li>Try updating MCP: <code>pip install --upgrade mcp</code></li>
                <li>Test server independently: <code>python3 run_server.py --help</code></li>
                <li>Use interactive mode even if server fails</li>
                <li>Check terminal output for detailed error messages</li>
            </ol>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <button class="button success" onclick="window.open('terminal://python3 run_host.py --interactive')">
                🚀 Launch Interactive Mode
            </button>
            <button class="button secondary" onclick="alert('Run: python3 test_host_standalone.py')">
                🧪 Run Tests
            </button>
        </div>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def root():
    return html_content

@app.get("/api/status")
async def get_status():
    try:
        from bio_mcp_host.llm_manager import LLMManager
        
        llm_manager = LLMManager()
        clients = llm_manager.list_clients()
        
        return {
            "status": "running",
            "available_llm_clients": clients,
            "server_connection": False,  # We know this is failing
            "message": "GUI is working, but use interactive mode for full features"
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "message": "Some components not available"
        }

def main():
    print("🌐 Starting Bio MCP Web GUI...")
    print("📍 Open http://localhost:8000 in your browser")
    print("💡 For full functionality, use: python3 run_host.py --interactive")
    print()
    
    uvicorn.run(app, host="localhost", port=8000, log_level="info")

if __name__ == "__main__":
    main()