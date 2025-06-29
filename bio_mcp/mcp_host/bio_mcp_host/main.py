#!/usr/bin/env python3
"""
Bio MCP Host - Entry point for the biological research MCP host
"""

import asyncio
import argparse
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to sys.path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bio_mcp_host.host import BioMCPHost

def load_environment():
    """Load environment variables from .env file"""
    # Look for .env file in current directory or parent directories
    current_dir = Path.cwd()
    env_file = current_dir / ".env"
    
    if not env_file.exists():
        # Try parent directory
        env_file = current_dir.parent / ".env"
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from: {env_file}")
    else:
        print("No .env file found. Make sure API keys are set in environment variables.")

async def interactive_mode(host: BioMCPHost):
    """Run in interactive mode for testing"""
    print("\n=== Bio MCP Host Interactive Mode ===")
    print("Commands:")
    print("  chat <message>     - Chat with the default LLM")
    print("  status            - Show host status")
    print("  tools             - List available tools")
    print("  clients           - List LLM clients")
    print("  upload <path>     - Upload a file")
    print("  files             - List uploaded files")
    print("  health            - Health check")
    print("  quit              - Exit")
    print()
    
    session_id = "interactive"
    
    while True:
        try:
            command = input("bio-mcp> ").strip()
            
            if not command:
                continue
            
            if command == "quit":
                break
            elif command == "status":
                status = host.get_status()
                print(json.dumps(status, indent=2))
            elif command == "tools":
                tools = host.get_available_tools()
                for tool in tools:
                    print(f"- {tool['name']}: {tool['description']}")
            elif command == "clients":
                clients = host.get_llm_clients()
                for name, info in clients.items():
                    status = "✓" if info.get("is_default") else " "
                    print(f"{status} {name}: {info['model']} ({info['provider']})")
            elif command == "files":
                result = await host.list_files()
                print(result.get("result", "No result"))
            elif command == "health":
                health = await host.health_check()
                print(json.dumps(health, indent=2))
            elif command.startswith("upload "):
                file_path = command[7:].strip()
                if os.path.exists(file_path):
                    result = await host.upload_file(file_path)
                    print(result.get("result", "Upload failed"))
                else:
                    print(f"File not found: {file_path}")
            elif command.startswith("chat "):
                message = command[5:].strip()
                if message:
                    print("Assistant: ", end="", flush=True)
                    async for chunk in host.chat_stream(session_id, message):
                        print(chunk, end="", flush=True)
                    print()  # New line after streaming
            else:
                print(f"Unknown command: {command}")
                
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit.")
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Bio MCP Host")
    parser.add_argument(
        "--server-command",
        default="python3 run_server.py",
        help="Command to start the Bio MCP Server"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode for testing"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind web server (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind web server (default: 8000)"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_environment()
    
    # Parse server command
    server_command = args.server_command.split()
    
    async def run_host():
        host = BioMCPHost(server_command)
        
        try:
            await host.start()
            
            if args.interactive:
                await interactive_mode(host)
            else:
                # Start web server (we'll implement this next)
                print(f"Starting web server on {args.host}:{args.port}")
                print("Web server not implemented yet. Use --interactive for now.")
                
                # Keep running
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\nShutting down...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("\n💡 The system can still work in limited mode!")
            print("   • LLM clients may still be available")
            print("   • Server tools will not be available")
            print("\n🔧 Troubleshooting:")
            print("   • Check if 'python3 run_server.py' works independently")
            print("   • Try updating MCP: pip install --upgrade mcp")
            
            if args.interactive:
                print("\n🚀 Starting in limited interactive mode anyway...")
                try:
                    await interactive_mode(host)
                except:
                    pass
            
            return 1
        finally:
            await host.stop()
        
        return 0
    
    try:
        exit_code = asyncio.run(run_host())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()