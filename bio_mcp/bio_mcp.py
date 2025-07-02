#!/usr/bin/env python3
"""
Bio MCP - Main entry point for the AI-powered biological research platform
"""

import argparse
import sys
import os
from pathlib import Path

def get_best_python():
    """Find the best Python executable to use"""
    # Common conda locations
    common_conda_roots = [
        Path.home() / 'anaconda3',
        Path.home() / 'miniconda3',
        Path('/opt/anaconda3'),
        Path('/opt/miniconda3'),
        Path('/usr/local/anaconda3'),
        Path('/usr/local/miniconda3')
    ]
    
    # Common environment names
    common_env_names = ['bio-mcp', 'biomcp', 'bio_mcp']
    
    # Try environment-specific Python first
    for conda_root in common_conda_roots:
        if conda_root.exists():
            for env_name in common_env_names:
                env_python = conda_root / 'envs' / env_name / 'bin' / 'python3'
                if env_python.exists():
                    return str(env_python)
            
            # Try base conda Python
            base_python = conda_root / 'bin' / 'python3'
            if base_python.exists():
                return str(base_python)
    
    # Fall back to system Python
    return 'python3'

def main():
    """Main entry point for Bio MCP"""
    parser = argparse.ArgumentParser(
        description="Bio MCP - AI-Powered Biological Research Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  bio_mcp.py interactive           # Start interactive mode
  bio_mcp.py server               # Start MCP server only  
  bio_mcp.py gui                  # Launch web GUI
  bio_mcp.py host --interactive   # Start host in interactive mode

For more information, see README.md
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Interactive command
    interactive_parser = subparsers.add_parser('interactive', help='Start interactive mode')
    
    # Server command  
    server_parser = subparsers.add_parser('server', help='Start MCP server only')
    
    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Launch web GUI')
    
    # Host command
    host_parser = subparsers.add_parser('host', help='Start host application')
    host_parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    host_parser.add_argument('--server-command', default='python3 run_server.py', help='Server command')
    
    args = parser.parse_args()
    
    if not args.command:
        # Default to interactive mode
        args.command = 'interactive'
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        if args.command == 'interactive':
            print("🚀 Starting Bio MCP in interactive mode...")
            python_cmd = get_best_python()
            os.system(f"{python_cmd} run_host.py --interactive")
            
        elif args.command == 'server':
            print("🔧 Starting Bio MCP server...")
            python_cmd = get_best_python()
            os.system(f"{python_cmd} run_server.py")
            
        elif args.command == 'gui':
            print("🌐 Starting Bio MCP web GUI...")
            python_cmd = get_best_python()
            os.system(f"{python_cmd} launch_gui.py")
            
        elif args.command == 'host':
            python_cmd = get_best_python()
            cmd = f"{python_cmd} run_host.py"
            if args.interactive:
                cmd += " --interactive"
            if args.server_command != 'python3 run_server.py':
                cmd += f" --server-command '{args.server_command}'"
            
            print(f"🚀 Starting Bio MCP host...")
            os.system(cmd)
            
    except KeyboardInterrupt:
        print("\n👋 Bio MCP stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()