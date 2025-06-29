#!/usr/bin/env python3
"""
Bio MCP Server - Entry point for the biological research MCP server
"""

import asyncio
import argparse
import sys
import os

# Add the mcp_server directory to the Python path  
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bio_mcp_server.server import BioMCPServer

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Bio MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio"], 
        default="stdio",
        help="Transport type (default: stdio)"
    )
    
    args = parser.parse_args()
    
    # Create and run server
    server = BioMCPServer()
    
    try:
        asyncio.run(server.run(args.transport))
    except KeyboardInterrupt:
        print("\nServer stopped.", file=sys.stderr)
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()