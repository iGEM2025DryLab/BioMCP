#!/usr/bin/env python3
"""
Test script for PyMOL and PROPKA tools
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from mcp_server.bio_mcp_server.tools.pymol_tool import PyMOLTool
from mcp_server.bio_mcp_server.tools.propka_tool import PropkaTool

async def test_tools():
    """Test both PyMOL and PROPKA tools"""
    print("🧪 Testing Bio MCP Tools...")
    
    # Initialize tools
    print("\n1. Initializing tools...")
    pymol_tool = PyMOLTool()
    propka_tool = PropkaTool()
    
    print(f"   PyMOL available: {pymol_tool.pymol_available}")
    print(f"   PyMOL executable: {pymol_tool.pymol_executable}")
    print(f"   PyMOL module mode: {pymol_tool.use_pymol_module}")
    print(f"   PROPKA available: {propka_tool.propka_available}")
    
    if not pymol_tool.pymol_available:
        print("❌ PyMOL not available")
    else:
        print("✅ PyMOL detected successfully")
        
    if not propka_tool.propka_available:
        print("❌ PROPKA not available") 
    else:
        print("✅ PROPKA detected successfully")
    
    # Check for test PDB file
    print("\n2. Looking for test PDB files...")
    test_files = [
        Path("bio_data/structures").glob("*.pdb"),
        Path("bio_data").glob("*.pdb"),
        Path(".").glob("*.pdb")
    ]
    
    pdb_file = None
    for file_glob in test_files:
        for file in file_glob:
            if file.exists():
                pdb_file = file
                break
        if pdb_file:
            break
    
    if pdb_file:
        print(f"   Found test file: {pdb_file}")
        
        # Test PyMOL visualization
        if pymol_tool.pymol_available:
            print("\n3. Testing PyMOL visualization...")
            try:
                result = await pymol_tool.create_visualization(
                    pdb_file_path=pdb_file,
                    style="cartoon",
                    width=400,
                    height=300
                )
                
                if result.get("success"):
                    print("✅ PyMOL visualization successful")
                    print(f"   Output: {result.get('file_path', 'N/A')}")
                else:
                    print(f"❌ PyMOL visualization failed: {result.get('error')}")
            except Exception as e:
                print(f"❌ PyMOL test error: {e}")
        
        # Test PROPKA calculation
        if propka_tool.propka_available:
            print("\n4. Testing PROPKA calculation...")
            try:
                result = await propka_tool.calculate_pka(
                    pdb_file_path=pdb_file,
                    ph=7.0
                )
                
                if result.get("success"):
                    print("✅ PROPKA calculation successful")
                    ionizable_groups = result.get("results", {}).get("ionizable_groups", [])
                    print(f"   Found {len(ionizable_groups)} ionizable groups")
                else:
                    print(f"❌ PROPKA calculation failed: {result.get('error')}")
            except Exception as e:
                print(f"❌ PROPKA test error: {e}")
    else:
        print("   No PDB files found for testing")
        print("   You can copy a test PDB file to test the tools")
    
    print("\n🏁 Tool testing complete!")

if __name__ == "__main__":
    asyncio.run(test_tools())