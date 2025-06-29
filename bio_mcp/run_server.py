#!/usr/bin/env python3
"""
Entry point for Bio MCP Server
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the server
if __name__ == "__main__":
    from mcp_server.bio_mcp_server.main import main
    main()