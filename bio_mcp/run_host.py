#!/usr/bin/env python3
"""
Entry point for Bio MCP Host
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the host
if __name__ == "__main__":
    from mcp_host.bio_mcp_host.main import main
    main()